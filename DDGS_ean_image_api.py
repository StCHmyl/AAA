import requests
import os
import time
import numpy as np
from PIL import Image as PILImage
from io import BytesIO
from ddgs import DDGS
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import cv2
import warnings

# 设置环境变量以避免CPU核心数检测警告
os.environ['LOKY_MAX_CPU_COUNT'] = '4'

def download_image_with_fallback(url, thumbnail_url, save_path=None, max_retries=3):
    """
    下载图片，添加重试机制和缩略图备选方案
    如果save_path为None，则返回图片内容而不保存到文件
    """
    image_data = None
    
    # 首先尝试下载原图
    if url:
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                # 使用PIL验证图片完整性
                img = PILImage.open(BytesIO(response.content))
                
                # 如果指定了保存路径则保存到文件
                if save_path:
                    img.save(save_path)
                
                image_data = response.content
                break
            except Exception as e:
                print(f"下载图片失败 {url} (尝试 {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
    
    # 如果原图下载失败，尝试下载缩略图
    if image_data is None and thumbnail_url:
        print(f"尝试下载缩略图替代: {thumbnail_url}")
        for attempt in range(max_retries):
            try:
                response = requests.get(thumbnail_url, timeout=10)
                response.raise_for_status()
                
                # 使用PIL验证图片完整性
                img = PILImage.open(BytesIO(response.content))
                
                # 如果指定了保存路径则保存到文件
                if save_path:
                    img.save(save_path)
                
                image_data = response.content
                break
            except Exception as e:
                print(f"下载缩略图失败 {thumbnail_url} (尝试 {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
    
    if image_data is None:
        print(f"下载图片最终失败，原图: {url}, 缩略图: {thumbnail_url}")
    
    return image_data

def search_product_images(ean, max_results=10):
    """
    使用DDGS搜索产品图片，获取更多候选图片用于聚类分析
    """
    try:
        keywords = ean
        
        # 使用DDGS搜索图片
        with DDGS() as ddgs:
            results = list(ddgs.images(keywords, max_results=max_results))
        print(f"找到 {len(results)} 张图片用于 EAN: {ean}")
            
        return results[:max_results]
    except Exception as e:
        print(f"搜索图片失败 {ean}: {str(e)}")
        return []

def extract_image_features(image_data):
    """
    从图片数据中提取特征用于聚类分析
    """
    try:
        # 使用OpenCV读取图片
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None
            
        # 调整图片大小以统一特征维度
        img = cv2.resize(img, (64, 64))
        
        # 提取颜色直方图特征
        hist_b = cv2.calcHist([img], [0], None, [8], [0, 256])
        hist_g = cv2.calcHist([img], [1], None, [8], [0, 256])
        hist_r = cv2.calcHist([img], [2], None, [8], [0, 256])
        
        # 展平并归一化直方图
        feature = np.concatenate([hist_b.flatten(), hist_g.flatten(), hist_r.flatten()])
        feature = feature / np.sum(feature)
        
        # 添加图像基本属性作为特征
        height, width = img.shape[:2]
        aspect_ratio = width / height
        feature = np.append(feature, [height, width, aspect_ratio])
        
        return feature
    except Exception as e:
        print(f"提取图片特征失败: {str(e)}")
        return None

def select_best_image(image_data_list):
    """
    从图片数据列表中选择最具代表性的单张图片
    """
    try:
        # 提取所有图片的特征
        features = []
        valid_image_data = []
        
        for data in image_data_list:
            feature = extract_image_features(data)
            if feature is not None:
                features.append(feature)
                valid_image_data.append(data)
        
        # 检查有效图片数量
        if len(valid_image_data) == 0:
            print("没有有效的图片可选择")
            return None
        elif len(valid_image_data) == 1:
            print("仅有一张有效图片，直接返回")
            return valid_image_data[0]  # 只有一张图片直接返回
        
        # 转换为numpy数组
        X = np.array(features)
        
        # 标准化特征
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # 执行K-means聚类，分成一个簇
        kmeans = KMeans(n_clusters=1, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        
        # 找到距离聚类中心最近的图片
        distances = []
        for i, feature in enumerate(X_scaled):
            distance = np.linalg.norm(feature - kmeans.cluster_centers_[0])
            distances.append((i, distance))
        
        # 选择距离中心最近的图片
        closest_idx, _ = min(distances, key=lambda x: x[1])
        best_image = valid_image_data[closest_idx]
        
        return best_image
    except Exception as e:
        print(f"选择最佳图片失败: {str(e)}")
        # 出错时回退到选择第一张图片
        return image_data_list[0] if image_data_list else None

def get_best_product_image(ean, temp_dir="temp"):
    """
    根据EAN条码获取最佳产品图片和元信息
    
    Args:
        ean (str): 产品EAN条码
        temp_dir (str): 临时目录路径，默认为"temp"
        
    Returns:
        dict: 包含最佳图片路径和元信息的字典
              {
                  'image_path': str,        # 最佳图片的存储路径
                  'metadata': dict          # 图片元信息
              }
              如果失败则返回None
    """
    print(f"处理EAN码: {ean}")
    
    # 创建临时目录
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    # 搜索更多图片用于分析
    image_results = search_product_images(ean, max_results=10)
    
    if not image_results:
        print(f"未找到EAN码 {ean} 的图片")
        return None
    
    # 下载所有候选图片
    downloaded_images = []
    
    for i, result in enumerate(image_results):
        img_url = result.get('image', '')
        thumbnail_url = result.get('thumbnail', '')
        
        if img_url or thumbnail_url:
            img_filename = f"{temp_dir}/{ean}_{i+1}.jpg"
            image_data = download_image_with_fallback(img_url, thumbnail_url, img_filename)
            
            if image_data:
                downloaded_images.append({
                    'path': img_filename,
                    'data': image_data,
                    'result': result,
                    'index': i
                })
    
    if not downloaded_images:
        print(f"EAN码 {ean} 没有成功下载任何图片")
        return None
    
    print(f"成功下载 {len(downloaded_images)} 张图片用于 {ean} 的分析")
    
    # 获取所有下载的图片数据
    image_data_list = [img['data'] for img in downloaded_images]
    
    # 选择最佳图片数据
    best_image_data = select_best_image(image_data_list)
    
    if not best_image_data:
        print(f"未能为EAN码 {ean} 选择到合适的图片")
        return None
    
    print(f"已选择最佳图片数据")
    
    # 查找被选中的图片的元信息和路径
    for img_info in downloaded_images:
        if img_info['data'] == best_image_data:
            # 返回最佳图片路径和元信息
            return {
                'image_path': img_info['path'],
                'metadata': img_info['result']
            }
    
    return None

def save_image_to_file(image_data, filename):
    """
    将图片数据保存到文件
    
    Args:
        image_data (bytes): 图片二进制数据
        filename (str): 保存的文件名
    """
    try:
        img = PILImage.open(BytesIO(image_data))
        img.save(filename)
        print(f"图片已保存到: {filename}")
    except Exception as e:
        print(f"保存图片失败: {str(e)}")

# 示例用法
if __name__ == "__main__":
    # 示例EAN码
    ean = "3346130022886"
    
    # 获取最佳图片和元信息
    result = get_best_product_image(ean)
    print(result)
    if result:
        # 打印图片路径
        print(f"最佳图片路径: {result['image_path']}")
        
        # 打印元信息
        metadata = result['metadata']
        print("\n元信息:")
        print(f"标题: {metadata.get('title', 'N/A')}")
        print(f"来源: {metadata.get('source', 'N/A')}")
        print(f"URL: {metadata.get('url', 'N/A')}")
        print(f"宽度: {metadata.get('width', 'N/A')}")
        print(f"高度: {metadata.get('height', 'N/A')}")
    else:
        print("未能获取到产品图片")