# routers/bill.py
from datetime import date, datetime, time, timedelta
from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from models import Bill
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas.bill import BillCreate, BillResponse
from typing import Union, List
from utils.bill import analyze_receipt
import asyncio
import calendar

from fastapi import APIRouter, Depends, Query
from datetime import date, timedelta
from sqlalchemy.orm import Session
from typing import Optional



router = APIRouter()

@router.post("/actions/bill")
async def analyze_bills(files: List[UploadFile] = File(...)):
    """
    批量上传图片并识别账单信息
    """
    results = []
    loop = asyncio.get_event_loop()
    
    for file in files:
        try:
            content = await file.read()
            # 在线程池中执行同步的分析函数
            data = await loop.run_in_executor(None, analyze_receipt, content)
            
            # 处理返回结果
            if isinstance(data, list):
                results.extend(data)
            elif isinstance(data, dict):
                # 过滤掉可能的错误信息，或者保留以便前端提示
                if "error" not in data:
                    results.append(data)
                else:
                    # 也可以选择返回包含错误的项，让前端显示失败
                    results.append({"error": data["error"], "filename": file.filename})
        except Exception as e:
            results.append({"error": str(e), "filename": file.filename})
            
    return results



@router.post("/bills", status_code=status.HTTP_201_CREATED)
def create_bill(
    bill_data: Union[BillCreate, List[BillCreate]], 
    db: Session = Depends(get_db)
):
    """
    创建账单（支持单个或多个）
    
    可以传入：
    1. 单个账单对象
    2. 账单对象数组
    """
    try:
        # 统一处理为列表
        bills_to_create = bill_data if isinstance(bill_data, list) else [bill_data]
        
        # 批量创建
        new_bills = []
        for bill in bills_to_create:
            new_bill = Bill(
                title=bill.title,
                merchant=bill.merchant,
                category=bill.category,
                amount=bill.amount,
                trade_time=bill.trade_time,
                remark=bill.remark,
                created_at=datetime.now()
            )
            new_bills.append(new_bill)
        
        # 批量添加到数据库
        db.add_all(new_bills)
        db.commit()
        
        # 刷新所有对象
        for bill in new_bills:
            db.refresh(bill)
        
        # 返回结果
        if isinstance(bill_data, list):
            # 如果传入的是数组，返回数组
            return {
                "success": True,
                "message": f"成功创建 {len(new_bills)} 条账单",
                "count": len(new_bills),
                "data": new_bills
            }
        else:
            # 如果传入的是单个对象，返回单个对象
            return {
                "success": True,
                "message": "账单创建成功",
                "data": new_bills[0]
            }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建账单失败: {str(e)}"
        )

@router.get("/bills")
def get_bills(
    range: Optional[str] = Query(None),
    query_date: Optional[date] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):

    # 默认今天
    today = query_date if query_date else date.today()

    # 根据 range 自动计算
    if range == "weekly":
        start_date = today - timedelta(days=6)
        end_date = today

    elif range == "monthly":
        # 本月第一天
        start_date = today.replace(day=1)
        # 本月最后一天
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day)

    # 如果只传 start_date
    if start_date and not end_date:
        end_date = today

    # 构建查询
    query = db.query(Bill)

    if start_date:
        query = query.filter(Bill.trade_time >= start_date)

    if end_date:
        query = query.filter(Bill.trade_time <= end_date)

    db_bills = (
        query.order_by(Bill.trade_time.desc(), Bill.id.desc())
        .all()
    )

    return {
        "bills": [
            {
                "id": db_bill.id,
                "amount": db_bill.amount,
                "category": db_bill.category,
                "merchant": db_bill.merchant,
                "title": db_bill.title,
                "trade_time": db_bill.trade_time,
                "remark": db_bill.remark
            }
            for db_bill in db_bills
        ]
    }
