from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


class BillCreate(BaseModel):
    """创建账单的请求模型"""
    title: str = Field(..., description="商品名称/交易标题", min_length=1, max_length=200)
    merchant: Optional[str] = Field(None, description="商户名称", max_length=200)
    category: str = Field(..., description="分类", max_length=255)
    amount: Decimal = Field(..., description="金额", gt=0)
    trade_time: date = Field(..., description="交易时间")
    remark: Optional[str] = Field(None, description="备注", max_length=500)

    @field_validator('amount')
    def validate_amount(cls, v):
        """验证金额格式（最多2位小数）"""
        if v <= 0:
            raise ValueError('金额必须大于0')
        # 保留两位小数
        return round(v, 2)
    
    


class BillResponse(BaseModel):
    """账单响应模型"""
    id: int
    title: str
    merchant: Optional[str] = None
    category: str
    amount: Decimal
    trade_time: date
    remark: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True  # Pydantic v2
        # orm_mode = True  # 如果你用的是 Pydantic v1，用这个