import os
import json
import logging

from utils.file_creator import create_default_configs, AI_MODELS_CONFIG, AI_PROVIDERS_CONFIG

logger = logging.getLogger(__name__)

_JSON_CACHE = {}


def _get_config_path(filename: str) -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', filename)


def _load_json_cached(path: str, default):
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return default

    cached = _JSON_CACHE.get(path)
    if cached and cached.get("mtime") == mtime:
        return cached.get("value", default)

    try:
        with open(path, 'r', encoding='utf-8') as f:
            value = json.load(f)
        _JSON_CACHE[path] = {"mtime": mtime, "value": value}
        return value
    except (FileNotFoundError, IOError, json.JSONDecodeError) as e:
        logger.error(f"加载JSON配置失败: {path}, error={e}")
        return default


def _atomic_write_json(path: str, value) -> None:
    dir_path = os.path.dirname(path)
    os.makedirs(dir_path, exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=4)
    os.replace(tmp_path, path)
    try:
        os.chmod(path, 0o600)
    except Exception:
        return


def load_ai_providers(type: str = "dict"):
    """
    加载AI提供商配置

    参数:
        type (str): 返回类型
            - "dict"/"json": 返回 {provider: {type, enabled, api_base, api_key}}
    """
    providers_path = _get_config_path('ai_providers.json')
    if not os.path.exists(providers_path):
        create_default_configs()

    providers_config = _load_json_cached(providers_path, AI_PROVIDERS_CONFIG)
    if type.lower() in ["dict", "json"]:
        if isinstance(providers_config, dict):
            return providers_config
        return AI_PROVIDERS_CONFIG
    return providers_config


def save_ai_providers(providers_config: dict) -> dict:
    """保存AI提供商配置（原子写入，避免写一半导致JSON损坏）"""
    providers_path = _get_config_path('ai_providers.json')
    _atomic_write_json(providers_path, providers_config)
    _JSON_CACHE.pop(providers_path, None)
    return providers_config


def load_ai_models(type="list"):
    """
    加载AI模型配置
    
    参数:
        type (str): 返回类型
            - "list": 返回所有模型的平铺列表 [model1, model2, ...]
            - "dict"/"json": 返回原始配置格式 {provider: [model1, model2, ...]}
    
    返回值:
        根据type参数返回不同格式的模型配置
    """
    try:
        models_path = _get_config_path('ai_models.json')
        
        # 如果配置文件不存在，创建默认配置
        if not os.path.exists(models_path):
            create_default_configs()
            
        models_config = _load_json_cached(models_path, AI_MODELS_CONFIG)
            
        # 根据type参数返回不同格式
        if type.lower() in ["dict", "json"]:
            return models_config
            
        # 默认返回模型列表
        all_models = []
        for provider, models in (models_config or {}).items():
            if not isinstance(models, list):
                continue
            all_models.extend([str(m).strip() for m in models if str(m).strip()])
                
        # 确保列表不为空
        if all_models:
            return all_models
                
    except (FileNotFoundError, IOError, json.JSONDecodeError) as e:
        logger.error(f"加载AI模型配置失败: {e}")
    
    # 如果出现任何问题，根据type返回默认值
    if type.lower() in ["dict", "json"]:
        return AI_MODELS_CONFIG
    
    # 默认返回模型列表
    return ["gpt-3.5-turbo", "gemini-1.5-flash", "claude-3-sonnet"]


def save_ai_models(models_config: dict) -> dict:
    """保存AI模型配置（原子写入，避免写一半导致JSON损坏）"""
    models_path = _get_config_path('ai_models.json')
    _atomic_write_json(models_path, models_config)
    _JSON_CACHE.pop(models_path, None)
    return models_config

def load_summary_times():
    """加载总结时间列表"""
    try:
        times_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'summary_times.txt')
        if not os.path.exists(times_path):
            create_default_configs()
            
        with open(times_path, 'r', encoding='utf-8') as f:
            times = [line.strip() for line in f if line.strip()]
            if times:
                return times
    except (FileNotFoundError, IOError) as e:
        logger.warning(f"summary_times.txt 加载失败: {e}，使用默认时间列表")
    return ['00:00', '06:00', '12:00', '18:00']

def load_delay_times():
    """加载延迟时间列表"""
    try:
        times_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'delay_times.txt')
        if not os.path.exists(times_path):
            create_default_configs()
            
        with open(times_path, 'r', encoding='utf-8') as f:
            times = [line.strip() for line in f if line.strip()]
            if times:
                return times
    except (FileNotFoundError, IOError) as e:
        logger.warning(f"delay_times.txt 加载失败: {e}，使用默认时间列表")
    return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

def load_max_media_size():
    """加载媒体大小限制"""
    try:
        size_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'max_media_size.txt')
        if not os.path.exists(size_path):
            create_default_configs()
            
        with open(size_path, 'r', encoding='utf-8') as f:
            size = [line.strip() for line in f if line.strip()]
            if size:
                return size
            
    except (FileNotFoundError, IOError) as e:
        logger.warning(f"max_media_size.txt 加载失败: {e}，使用默认大小限制")
    return [5,10,15,20,50,100,200,300,500,1024,2048]


def load_media_extensions():
    """加载媒体扩展名"""
    try:
        size_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'media_extensions.txt')
        if not os.path.exists(size_path):
            create_default_configs()
            
        with open(size_path, 'r', encoding='utf-8') as f:
            size = [line.strip() for line in f if line.strip()]
            if size:
                return size
            
    except (FileNotFoundError, IOError) as e:
        logger.warning(f"media_extensions.txt 加载失败: {e}，使用默认扩展名")
    return ['无扩展名','txt','jpg','png','gif','mp4','mp3','wav','ogg','flac','aac','wma','m4a','m4v','mov','avi','mkv','webm','mpg','mpeg','mpe','mp3','mp2','m4a','m4p','m4b','m4r','m4v','mpg','mpeg','mp2','mp3','mp4','mpc','oga','ogg','wav','wma','3gp','3g2','3gpp','3gpp2','amr','awb','caf','flac','m4a','m4b','m4p','oga','ogg','opus','spx','vorbis','wav','wma','webm','aac','ac3','dts','dtshd','flac','mp3','mp4','m4a','m4b','m4p','oga','ogg','wav','wma','webm','aac','ac3','dts','dtshd','flac','mp3','mp4','m4a','m4b','m4p','oga','ogg','wav','wma','webm']
