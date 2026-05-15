from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseSearchStrategy(ABC):
    """
    Lớp cơ sở cho tất cả các chiến thuật tìm kiếm.
    Đảm bảo mọi strategy đều có chung interface để Orchestrator dễ dàng điều phối.
    """
    
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Thực hiện tìm kiếm và trả về danh sách jobs chi tiết.
        
        Args:
            query: Câu hỏi hoặc từ khóa của người dùng.
            **kwargs: Các tham số bổ sung như top_k, category, filters...
            
        Returns:
            List[Dict[str, Any]]: Danh sách các công việc đã được format đầy đủ.
        """
        pass

    def get_name(self) -> str:
        """Trả về tên của chiến thuật (để logging/tracking)"""
        return self.__class__.__name__
