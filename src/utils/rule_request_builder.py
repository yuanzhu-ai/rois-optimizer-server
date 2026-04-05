"""
Rule请求构建器模块，用于构建不同Rule类型的请求数据
"""
from typing import Dict, Any, List, Optional


class RuleRequestBuilder:
    """Rule请求构建器"""
    
    @staticmethod
    def build_change_flight_request(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建change_flight类型的请求数据
        
        格式:
        {
          "worksetId": 0,
          "filiale": "BR",
          "division": "P",
          "flightIds": [162906, 162218, 162905, 162748, 162638, 162736, 163835, 163775, 163695, 163769]
        }
        
        Args:
            parameters: 输入参数
            
        Returns:
            构建好的请求数据
        """
        return {
            "worksetId": 0,
            "filiale": parameters.get("airline", ""),
            "division": parameters.get("division", ""),
            "flightIds": [int(id) for id in parameters.get("fltId", "").split(",") if id.strip()]
        }
    
    @staticmethod
    def build_manday_request(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建manday类型的请求数据
        
        格式:
        {
          "worksetId": 0,
          "strDtLoc": "2025-02-01",
          "endDtLoc": "2025-03-30",
          "division": "P"
        }
        
        Args:
            parameters: 输入参数
            
        Returns:
            构建好的请求数据
        """
        return {
            "worksetId": 0,
            "strDtLoc": parameters.get("startDt", ""),
            "endDtLoc": parameters.get("endDt", ""),
            "division": parameters.get("division", "")
        }
    
    @staticmethod
    def build_manday_byCrew_request(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建manday_byCrew类型的请求数据
        
        格式:
        {
          "worksetId": 0,
          "start": "2024-09-12",
          "end": "2024-09-30",
          "division": "P",
          "crewIds": ["I73313", "H47887", "I73647", "E53500"]
        }
        
        Args:
            parameters: 输入参数
            
        Returns:
            构建好的请求数据
        """
        return {
            "worksetId": 0,
            "start": parameters.get("startDt", ""),
            "end": parameters.get("endDt", ""),
            "division": parameters.get("division", ""),
            "crewIds": [id.strip() for id in parameters.get("crewIds", "").split(",") if id.strip()]
        }
    
    @staticmethod
    def build_request(rule_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据Rule类型构建请求数据
        
        Args:
            rule_type: Rule类型（change_flight, manday, manday_byCrew）
            parameters: 输入参数
            
        Returns:
            构建好的请求数据
            
        Raises:
            ValueError: 不支持的Rule类型
        """
        if rule_type == "change_flight":
            return RuleRequestBuilder.build_change_flight_request(parameters)
        elif rule_type == "manday":
            return RuleRequestBuilder.build_manday_request(parameters)
        elif rule_type == "manday_byCrew":
            return RuleRequestBuilder.build_manday_byCrew_request(parameters)
        elif rule_type == "manday byCrew":
            # 兼容旧格式
            return RuleRequestBuilder.build_manday_byCrew_request(parameters)
        else:
            raise ValueError(f"不支持的Rule类型: {rule_type}")
