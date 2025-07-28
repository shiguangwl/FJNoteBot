"""
Blinko API Service Layer - Blinko API 服务层
本模块采用仓储模式（Repository Pattern）封装了对 Blinko API 的所有网络请求。
- IBlinkoRepository: 定义了与笔记数据交互的统一接口。
- BlinkoApiClient: 实现了该接口，负责具体的 HTTP 请求和响应处理。
这种设计将数据访问逻辑与业务逻辑解耦，使得上层代码不关心数据来源是网络 API 还是数据库。
"""

import aiohttp
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

from ..core.models import NoteType
from ..core.exceptions import BlinkoApiException


class IBlinkoRepository(ABC):
    """
    Blinko 仓储接口
    定义了所有与 Blinko 笔记服务交互的标准操作。
    """
    
    @abstractmethod
    async def create_note(self, content: str, note_type: int = 0, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        创建一个新的笔记。
        
        :param content: 笔记内容，Blinko 会自动从中解析 #标签。
        :param note_type: 笔记类型（闪念、ToDo等）。
        :param tags: 附加的标签列表（通常为空，让Blinko从内容解析）。
        :return: API 响应字典。
        """
        pass
    
    @abstractmethod
    async def list_notes(self, page: int = 1, size: int = 30, note_type: int = -1, tag_id: Optional[int] = None, archived_status: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        获取笔记列表。
        
        :param page: 页码。
        :param size: 每页数量。
        :param note_type: 笔记类型过滤。
        :param tag_id: 标签ID过滤。
        :param archived_status: 归档状态过滤 (True: 已归档, False: 未归档, None: 所有)。
        :return: 笔记对象字典的列表。
        """
        pass
    
    @abstractmethod
    async def update_note(self, note_id: int, content: Optional[str] = None, note_type: Optional[int] = None, tags: Optional[List[str]] = None, is_archived: Optional[bool] = None) -> Dict[str, Any]:
        """
        更新一个已存在的笔记，支持部分更新。
        
        :param note_id: 要更新的笔记的唯一ID。
        :param content: 新的笔记内容。
        :param note_type: 新的笔记类型。
        :param tags: 新的标签列表。
        :param is_archived: 新的归档状态。
        :return: API 响应字典。
        """
        pass
    
    @abstractmethod
    async def delete_note(self, note_id: int) -> Dict[str, Any]:
        """删除笔记"""
        pass
    
    @abstractmethod
    async def search_notes(self, query: str) -> Dict[str, Any]:
        """搜索笔记"""
        pass
    
    @abstractmethod
    async def list_tags(self) -> Dict[str, Any]:
        """获取标签列表"""
        pass
    
    @abstractmethod
    async def upload_file(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """上传文件"""
        pass


class BlinkoApiClient(IBlinkoRepository):
    """
    Blinko API 客户端实现
    负责与 Blinko 后端进行实际的 HTTP 通信。
    """
    
    def __init__(self, base_url: str, token: str):
        """
        初始化 API 客户端。
        
        :param base_url: Blinko API 的基础 URL。
        :param token: 用于认证的 Bearer Token。
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """
        获取 aiohttp.ClientSession 实例。
        采用延迟初始化（Lazy Initialization）和单例模式，确保只在需要时创建一个共享的会话。
        """
        if self.session is None or self.session.closed:
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        统一的请求方法，封装了请求的发送、错误处理和响应解析。
        
        :param method: HTTP 请求方法 (e.g., "GET", "POST").
        :param endpoint: API 的端点路径 (e.g., "/v1/note/list").
        :param kwargs: 传递给 aiohttp.ClientSession.request 的其他参数。
        :return: 解析后的 JSON 响应字典。
        :raises BlinkoApiException: 当网络错误或 API 返回错误状态码时抛出。
        """
        session = await self._get_session()
        url = f"{self.base_url}/api{endpoint}"
        
        try:
            async with session.request(method, url, **kwargs) as response:
                if response.status >= 400:
                    text = await response.text()
                    raise BlinkoApiException(f"API request failed: {response.status} - {text}")
                return await response.json()
        except aiohttp.ClientError as e:
            raise BlinkoApiException(f"Network error: {str(e)}")
    
    async def create_note(self, content: str, note_type: int = 0, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """创建笔记"""
        data = {
            "content": content,
            "type": note_type
        }
        # 不传递tags数组，让Blinko从content中自动解析标签
        return await self._request("POST", "/v1/note/upsert", json=data)
    
    async def list_notes(self, page: int = 1, size: int = 30, note_type: int = -1, tag_id: Optional[int] = None, archived_status: Optional[bool] = None) -> List[Dict[str, Any]]:
        """获取笔记列表"""
        data = {
            "page": page,
            "size": size * 5,  # 获取更多记录(e.g. 150)以便在客户端进行更可靠的过滤
            "tagId": tag_id,
            "orderBy": "desc"
        }
        # 注意：blinko API 的 type 过滤似乎不工作，所以我们在客户端过滤
        
        result = await self._request("POST", "/v1/note/list", json=data)
        
        # 如果API返回的是直接的数组
        if isinstance(result, list):
            notes = result
        else:
            notes = result.get("notes", [])
        
        # 客户端过滤类型
        if note_type != -1:
            notes = [note for note in notes if note.get("type") == note_type]
        
        # 新增: 按归档状态过滤
        if archived_status is not None:
            notes = [note for note in notes if note.get("isArchived") == archived_status]
        
        # 限制返回数量
        return notes[:size]
    
    async def update_note(self, note_id: int, content: Optional[str] = None, note_type: Optional[int] = None, tags: Optional[List[str]] = None, is_archived: Optional[bool] = None) -> Dict[str, Any]:
        """更新笔记，支持部分更新"""
        data = {"id": note_id}
        if content is not None:
            data["content"] = content
        if note_type is not None:
            data["type"] = note_type
        if tags is not None:
            data["tags"] = tags
        if is_archived is not None:
            data["isArchived"] = is_archived
        
        return await self._request("POST", "/v1/note/upsert", json=data)
    
    async def delete_note(self, note_id: int) -> Dict[str, Any]:
        """删除笔记"""
        data = {"noteIds": [note_id]}
        return await self._request("POST", "/v1/note/batch-delete", json=data)
    
    async def search_notes(self, query: str) -> List[Dict[str, Any]]:
        """搜索笔记"""
        data = {
            "page": 1,
            "size": 9999,
            "searchText": query,
            "orderBy": "desc"
        }
        result = await self._request("POST", "/v1/note/list", json=data)
        
        # 如果API返回的是直接的数组
        if isinstance(result, list):
            return result
        else:
            return result.get("notes", [])
    
    async def list_tags(self) -> Dict[str, Any]:
        """获取标签列表"""
        return await self._request("GET", "/v1/tags/list")
    
    async def upload_file(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """上传文件"""
        session = await self._get_session()
        url = f"{self.base_url}/api/v1/file/upload"
        
        data = aiohttp.FormData()
        data.add_field('file', file_data, filename=filename)
        
        async with session.post(url, data=data) as response:
            if response.status >= 400:
                text = await response.text()
                raise BlinkoApiException(f"File upload failed: {response.status} - {text}")
            return await response.json()
    
    async def close(self):
        """关闭连接"""
        if self.session and not self.session.closed:
            await self.session.close()