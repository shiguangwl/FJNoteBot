"""
Blinko API service layer
Blinko API 服务层，采用仓储模式
"""

import aiohttp
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

from ..core.models import NoteType
from ..core.exceptions import BlinkoApiException


class IBlinkoRepository(ABC):
    """Blinko 仓储接口"""
    
    @abstractmethod
    async def create_note(self, content: str, note_type: int = 0, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """创建笔记"""
        pass
    
    @abstractmethod
    async def list_notes(self, page: int = 1, size: int = 30, note_type: int = -1, tag_id: Optional[int] = None) -> Dict[str, Any]:
        """获取笔记列表"""
        pass
    
    @abstractmethod
    async def update_note(self, note_id: int, content: str, note_type: int = 0, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """更新笔记"""
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
    """Blinko API 客户端实现"""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取 HTTP 会话（单例模式）"""
        if self.session is None or self.session.closed:
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """统一请求方法"""
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
    
    async def list_notes(self, page: int = 1, size: int = 30, note_type: int = -1, tag_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取笔记列表"""
        data = {
            "page": page,
            "size": size * 2,  # 获取更多记录以便过滤
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
        
        # 限制返回数量
        return notes[:size]
    
    async def update_note(self, note_id: int, content: str, note_type: int = 0, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """更新笔记"""
        data = {
            "id": note_id,
            "content": content,
            "type": note_type,
            "tags": tags or []
        }
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