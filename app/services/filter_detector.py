"""
Filter Detection Service
Phát hiện các bộ lọc công việc từ query của người dùng
"""
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

@dataclass
class JobFilter:
    """Chứa các bộ lọc công việc được phát hiện"""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    location: Optional[str] = None
    company_size: Optional[str] = None
    remote: Optional[bool] = None
    keywords: Optional[str] = None
    
    def has_filters(self) -> bool:
        """Kiểm tra có bộ lọc nào không"""
        return any([
            self.salary_min is not None,
            self.salary_max is not None,
            self.location is not None,
            self.company_size is not None,
            self.remote is not None,
            self.keywords is not None
        ])
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển thành dict cho logging"""
        return {
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "location": self.location,
            "company_size": self.company_size,
            "remote": self.remote,
            "keywords": self.keywords
        }


class FilterDetector:
    """Phát hiện bộ lọc từ query"""
    
    # Salary patterns
    SALARY_PATTERNS = [
        # Range patterns
        r"lương\s*(\d+)\s*-\s*(\d+)\s*(triệu|tr|vnđ)",
        r"(\d+)\s*-\s*(\d+)\s*(triệu|tr|vnđ)",
        
        # Min salary patterns
        r"lương\s*từ\s*([0-9]+)\s*(triệu|tr|vnđ)",
        r"lương\s*(từ)\s*([0-9]+)\s*(triệu|tr|vnđ)",
        r"từ\s*([0-9]+)\s*(triệu|tr|vnđ)\s*(trở lên|từ)?",
        r"(\d+)\s*(triệu|tr|vnđ)\s*(trở lên|từ)",
        
        # Max salary patterns  
        r"lương\s*đến\s*([0-9]+)\s*(triệu|tr|vnđ)",
        r"lương\s*tối đa\s*([0-9]+)\s*(triệu|tr|vnđ)",
        
        # Above/below patterns
        r"lương\s*trên\s*([0-9]+)\s*(triệu|tr|vnđ)",
        r"lương\s*(trên|cao hơn)\s*([0-9]+)\s*(triệu|tr|vnđ)",
        r"trên\s*([0-9]+)\s*(triệu|tr|vnđ)",
        r"cao hơn\s*([0-9]+)\s*(triệu|tr|vnđ)",
        
        # Simple patterns
        r"lương\s*([0-9]+)\s*(triệu|tr|vnđ)",
        r"([0-9]+)\s*(triệu|tr|vnđ)"
    ]
    
    # Location patterns
    LOCATION_KEYWORDS = {
        "hà nội": ["hà nội", "hn", "hanoi", "ha noi", "thủ đô", "thành phố hà nội", "tp hà nội"],
        "hồ chí minh": ["hồ chí minh", "hcm", "saigon", "tp.hcm", "thành phố hồ chí minh", "ho chi minh", "tp hcm"],
        "đà nẵng": ["đà nẵng", "dn", "danang", "tp đà nẵng"],
        "quận 1": ["quận 1", "q1", "quận nhất", "quận 1", "q.1"],
        "quận 3": ["quận 3", "q3", "quận ba", "quận 3", "q.3"],
        "cầu giấy": ["cầu giấy", "cau giay", "quận cầu giấy"],
        "bình thạnh": ["bình thạnh", "binh thanh", "quận bình thạnh"],
        "thủ đức": ["thủ đức", "thu duc", "tp thủ đức"],
        "long biên": ["long biên"],
        "tây hồ": ["tây hồ"],
        "ba đình": ["ba đình"]
    }
    
    # Company size patterns
    COMPANY_SIZE_KEYWORDS = {
        "startup": ["startup", "start up", "khởi nghiệp", "khởi sáng tạo", "doanh nghiệp mới", "công ty khởi nghiệp", "start-up", "start up"],
        "lớn": ["lớn", "big", "large", "enterprise", "tập đoàn", "tổng công ty", "doanh nghiệp lớn", "công ty quốc tế", "multinational"],
        "nhỏ": ["nhỏ", "small", "sme", "doanh nghiệp vừa và nhỏ", "doanh nghiệp nhỏ", "công ty gia đình", "công ty con"],
        "vừa": ["vừa", "medium", "mid-size", "doanh nghiệp trung bình", "công ty trung bình"]
    }
    
    # Remote patterns
    REMOTE_KEYWORDS = [
        "remote", "làm việc tại nhà", "work from home", "wfh", "online", "từ xa",
        "làm việc từ xa", "làm việc online", "làm việc kết nối trực tuyến",
        "làm việc hybrid", "linh hoạt", "không cần đến văn phòng",
        "làm ở nhà", "làm việc trực tuyến", "không phải đi làm",
        "work from home", "hybrid working", "flexible working"
    ]
    
    def detect_filters(self, query: str) -> JobFilter:
        """
        Phát hiện bộ lọc từ query
        
        Args:
            query: Query từ người dùng
            
        Returns:
            JobFilter: Bộ lọc được phát hiện
        """
        query_lower = query.lower()
        job_filter = JobFilter()
        
        # Detect salary
        salary_min, salary_max = self._detect_salary(query_lower)
        job_filter.salary_min = salary_min
        job_filter.salary_max = salary_max
        
        # Detect location
        job_filter.location = self._detect_location(query_lower)
        
        # Detect company size
        job_filter.company_size = self._detect_company_size(query_lower)
        
        # Detect remote
        job_filter.remote = self._detect_remote(query_lower)
        
        # Extract keywords (remove detected filters)
        job_filter.keywords = self._extract_keywords(query, job_filter)
        
        logger.info(f"Detected filters: {job_filter.to_dict()}")
        return job_filter
    
    def _detect_salary(self, query: str) -> tuple[Optional[int], Optional[int]]:
        """Phát hiện lương từ query"""
        for pattern in self.SALARY_PATTERNS:
            match = re.search(pattern, query)
            if match:
                groups = match.groups()
                matched_text = match.group(0)  # Full matched text
                
                # Handle range patterns (min-max) - only if both groups are numbers
                if len(groups) >= 2 and groups[0] and groups[1]:
                    # Check if both groups are numeric (for patterns like "10-20")
                    if groups[0].isdigit() and groups[1].isdigit():
                        try:
                            min_salary = int(groups[0])
                            max_salary = int(groups[1])
                            return min_salary, max_salary
                        except ValueError:
                            continue
                    else:
                        # This is not a range pattern (e.g., "10 triệu"), continue to single value logic
                        pass
                
                # Handle single value patterns
                for group in groups:
                    if group and group.isdigit():
                        try:
                            salary = int(group)
                            # Determine if it's min or max based on matched text
                            if any(keyword in matched_text.lower() for keyword in ["từ", "trên", "cao hơn", "trở lên"]):
                                return salary, None
                            elif any(keyword in matched_text.lower() for keyword in ["đến", "tối đa"]):
                                return None, salary
                            else:
                                # Default to min salary for ambiguous cases
                                return salary, None
                        except ValueError:
                            continue
        
        return None, None
    
    def _detect_location(self, query: str) -> Optional[str]:
        """Phát hiện địa điểm từ query"""
        for location, keywords in self.LOCATION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query:
                    return location
        return None
    
    def _detect_company_size(self, query: str) -> Optional[str]:
        """Phát hiện kích thước công ty từ query"""
        for size, keywords in self.COMPANY_SIZE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query:
                    return size
        return None
    
    def _detect_remote(self, query: str) -> Optional[bool]:
        """Phát hiện yêu cầu remote từ query"""
        for keyword in self.REMOTE_KEYWORDS:
            if keyword in query:
                return True
        return None
    
    def _extract_keywords(self, query: str, job_filter: JobFilter) -> Optional[str]:
        """Trích xuất keywords sau khi loại bỏ filters"""
        keywords = query
        
        # Remove salary patterns
        for pattern in self.SALARY_PATTERNS:
            keywords = re.sub(pattern, "", keywords, flags=re.IGNORECASE)
        
        # Remove location keywords
        for location_keywords in self.LOCATION_KEYWORDS.values():
            for keyword in location_keywords:
                keywords = keywords.replace(keyword, "")
        
        # Remove company size keywords
        for size_keywords in self.COMPANY_SIZE_KEYWORDS.values():
            for keyword in size_keywords:
                keywords = keywords.replace(keyword, "")
        
        # Remove remote keywords
        for keyword in self.REMOTE_KEYWORDS:
            keywords = keywords.replace(keyword, "")
        
        # Clean up
        keywords = re.sub(r'\s+', ' ', keywords).strip()
        
        return keywords if keywords and len(keywords) > 2 else None


# Singleton instance
filter_detector = FilterDetector()


def detect_job_filters(query: str) -> JobFilter:
    """
    Detect job filters from query (convenience function)
    
    Args:
        query: User query
        
    Returns:
        JobFilter: Detected filters
    """
    return filter_detector.detect_filters(query)
