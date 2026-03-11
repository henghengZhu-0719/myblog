import React, { useState, useEffect, useMemo } from 'react';
import { analyzeBills, createBill, getBills } from '../api';
import ReactECharts from 'echarts-for-react';

function Bills() {
  const [bills, setBills] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  
  // 查询范围控制
  const [dateRange, setDateRange] = useState('weekly'); // 'weekly' or 'monthly'
  // 当前查询基准日期（默认今天）
  const [queryDate, setQueryDate] = useState(() => {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  });
  
  const [selectedDate, setSelectedDate] = useState(null);
  const [chartType, setChartType] = useState('bar'); // 'bar' or 'pie'
  
  // 识别结果暂存
  const [recognizedBills, setRecognizedBills] = useState([]);
  
  const categories = [
    "餐饮", "交通", "购物", "居家", "娱乐", "医疗", "其他"
  ];

  const fetchBills = async () => {
    setLoading(true);
    try {
      // 传递查询日期和范围
      const response = await getBills(queryDate, dateRange);
      setBills(response.data.bills || []);
      // 默认选中查询日期
      setSelectedDate(queryDate);
    } catch (err) {
      console.error('Failed to fetch bills:', err);
      // setError('获取账单失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBills();
  }, [queryDate, dateRange]); // 当查询日期或范围变化时重新获取

  // 1. 处理柱状图数据 (根据范围动态计算)
  const barChartOption = useMemo(() => {
    if (bills.length === 0) return null;

    // 根据 dateRange 决定显示哪些天的数据
    const days = [];
    if (dateRange === 'weekly') {
      // 近七天 (今天 + 前6天)
      for (let i = 6; i >= 0; i--) {
        const d = new Date(queryDate);
        d.setDate(d.getDate() - i);
        days.push(d.toISOString().split('T')[0]);
      }
    } else {
      // 本月 (从月初到月末)
      // 注意：这里我们简化逻辑，显示 queryDate 所在月份的所有天数
      // 或者是从月初到今天？通常"月度账单"是指整个自然月
      const d = new Date(queryDate);
      const year = d.getFullYear();
      const month = d.getMonth(); // 0-11
      const lastDay = new Date(year, month + 1, 0).getDate(); // 获取当月最后一天
      
      for (let i = 1; i <= lastDay; i++) {
        const dayStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
        days.push(dayStr);
      }
    }

    // 统计每天的总金额
    const dailyAmounts = days.map(day => {
      const dayBills = bills.filter(b => b.trade_time === day);
      const total = dayBills.reduce((sum, b) => sum + Number(b.amount), 0);
      return {
        date: day,
        amount: parseFloat(total.toFixed(2)),
        // 获取星期几
        weekday: new Date(day).toLocaleDateString('zh-CN', { weekday: 'short' })
      };
    });

    return {
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          const data = params[0].data;
          return `${data.date} (${data.weekday})<br/>总支出: ¥${data.value}`;
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: dailyAmounts.map(d => dateRange === 'weekly' ? `${d.weekday}\n${d.date.slice(5)}` : d.date.slice(8)), // 月度只显示日
        axisLabel: {
          interval: dateRange === 'weekly' ? 0 : 'auto', // 月度数据自动间隔
          rotate: 0 
        }
      },
      yAxis: {
        type: 'value',
        name: '金额 (元)'
      },
      dataZoom: [
        {
          type: 'inside',
          start: 0, 
          end: 100
        },
        {
          start: 0,
          end: 100,
          handleSize: '80%',
          show: dateRange === 'monthly' // 仅月度显示缩放条
        }
      ],
      series: [
        {
          data: dailyAmounts.map(d => ({
            value: d.amount,
            date: d.date,
            weekday: d.weekday,
            itemStyle: {
              color: d.date === selectedDate ? '#28a745' : '#5470c6'
            }
          })),
          type: 'bar',
          barWidth: dateRange === 'weekly' ? '40%' : '60%',
          label: {
            show: dateRange === 'weekly', // 月度太挤不显示数值
            position: 'top',
            formatter: '¥{c}'
          }
        }
      ]
    };
  }, [bills, queryDate, selectedDate, dateRange]);

  // 2. 处理饼图数据
  const pieChartOption = useMemo(() => {
    if (bills.length === 0) return null;

    // 过滤出当前范围内的数据
    let rangeBills = [];
    
    if (dateRange === 'weekly') {
      const rangeStart = new Date(queryDate);
      rangeStart.setDate(rangeStart.getDate() - 6);
      const rangeStartDateStr = rangeStart.toISOString().split('T')[0];
      rangeBills = bills.filter(b => b.trade_time >= rangeStartDateStr && b.trade_time <= queryDate);
    } else {
      // 月度：过滤出 queryDate 所在月份的所有账单
      const targetMonth = queryDate.slice(0, 7); // "YYYY-MM"
      rangeBills = bills.filter(b => b.trade_time.startsWith(targetMonth));
    }

    // 统计各分类总金额
    const categoryMap = {};
    rangeBills.forEach(bill => {
      const cat = bill.category || '其他';
      categoryMap[cat] = (categoryMap[cat] || 0) + Number(bill.amount);
    });

    const pieData = Object.entries(categoryMap).map(([name, value]) => ({
      name,
      value: parseFloat(value.toFixed(2))
    }));

    return {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: ¥{c} ({d}%)'
      },
      legend: {
        orient: 'horizontal',
        bottom: 'bottom'
      },
      series: [
        {
          type: 'pie',
          radius: '50%',
          data: pieData,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }
      ]
    };
  }, [bills, queryDate, dateRange]);

  // 处理图表点击事件
  const onChartClick = (params) => {
    if (chartType === 'bar' && params.data && params.data.date) {
      setSelectedDate(params.data.date);
    }
  };

  // 过滤显示选中日期的账单
  const displayedBills = useMemo(() => {
    if (!selectedDate) return bills;
    return bills.filter(b => b.trade_time === selectedDate);
  }, [bills, selectedDate]);

  const handleFileChange = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    setUploading(true);
    setError('');
    
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    try {
      const response = await analyzeBills(formData);
      const newBills = response.data;
      
      // 为每个识别出的账单添加临时ID，方便编辑
      const billsWithId = newBills.map((bill, index) => ({
        ...bill,
        tempId: Date.now() + index,
        amount: bill.amount || 0,
        trade_time: bill.trade_time || new Date().toISOString().split('T')[0]
      }));
      
      setRecognizedBills(prev => [...prev, ...billsWithId]);
      
    } catch (err) {
      console.error('Failed to analyze bills:', err);
      setError('识别账单失败，请重试');
    } finally {
      setUploading(false);
      // 清空 input
      e.target.value = null;
    }
  };

  const handleBillChange = (id, field, value) => {
    setRecognizedBills(prev => prev.map(bill => 
      bill.tempId === id ? { ...bill, [field]: value } : bill
    ));
  };

  const handleRemoveRecognized = (id) => {
    setRecognizedBills(prev => prev.filter(bill => bill.tempId !== id));
  };

  const handleSaveBills = async () => {
    if (recognizedBills.length === 0) return;

    try {
      // 移除 tempId 和 error 字段
      const billsToSave = recognizedBills.map(({ tempId, error, filename, ...rest }) => rest);
      
      await createBill(billsToSave);
      
      alert('账单保存成功！');
      setRecognizedBills([]);
      fetchBills(); // 刷新列表
    } catch (err) {
      console.error('Failed to save bills:', err);
      alert('保存账单失败: ' + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div>
      <div className="card">
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px'}}>
          <h2 style={{margin: 0}}>智能记账</h2>
          <div>
            <input
              type="file"
              multiple
              accept="image/*"
              onChange={handleFileChange}
              style={{display: 'none'}}
              id="file-upload"
            />
            <label 
              htmlFor="file-upload" 
              style={{
                cursor: 'pointer', 
                backgroundColor: '#007bff', 
                color: 'white', 
                padding: '8px 16px', 
                borderRadius: '4px',
                fontSize: '14px',
                display: 'inline-block'
              }}
            >
              {uploading ? '正在识别...' : '上传票据'}
            </label>
          </div>
        </div>

        {error && <div className="error">{error}</div>}

        {/* 待确认账单区域 */}
        {recognizedBills.length > 0 && (
          <div style={{marginBottom: '30px', padding: '15px', border: '1px solid #eee', borderRadius: '8px'}}>
            <h3 style={{marginTop: 0}}>待确认账单 ({recognizedBills.length})</h3>
            <div style={{overflowX: 'auto'}}>
              <table style={{width: '100%', borderCollapse: 'collapse', minWidth: '800px'}}>
                <thead>
                  <tr style={{background: '#f8f9fa', textAlign: 'left'}}>
                    <th style={{padding: '10px'}}>日期</th>
                    <th style={{padding: '10px'}}>标题</th>
                    <th style={{padding: '10px'}}>商户</th>
                    <th style={{padding: '10px'}}>分类</th>
                    <th style={{padding: '10px'}}>金额</th>
                    <th style={{padding: '10px'}}>备注</th>
                    <th style={{padding: '10px'}}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {recognizedBills.map(bill => (
                    <tr key={bill.tempId} style={{borderBottom: '1px solid #eee'}}>
                      <td style={{padding: '5px'}}>
                        <input 
                          type="date" 
                          value={bill.trade_time}
                          onChange={(e) => handleBillChange(bill.tempId, 'trade_time', e.target.value)}
                          style={{width: '130px'}}
                        />
                      </td>
                      <td style={{padding: '5px'}}>
                        <input 
                          type="text" 
                          value={bill.title || ''}
                          onChange={(e) => handleBillChange(bill.tempId, 'title', e.target.value)}
                          placeholder="必填"
                          style={{width: '100%'}}
                        />
                      </td>
                      <td style={{padding: '5px'}}>
                        <input 
                          type="text" 
                          value={bill.merchant || ''}
                          onChange={(e) => handleBillChange(bill.tempId, 'merchant', e.target.value)}
                          style={{width: '100%'}}
                        />
                      </td>
                      <td style={{padding: '5px'}}>
                        <select 
                          value={bill.category || ''}
                          onChange={(e) => handleBillChange(bill.tempId, 'category', e.target.value)}
                          style={{width: '100%'}}
                        >
                          <option value="">请选择</option>
                          {categories.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                      </td>
                      <td style={{padding: '5px'}}>
                        <input 
                          type="number" 
                          value={bill.amount}
                          onChange={(e) => handleBillChange(bill.tempId, 'amount', parseFloat(e.target.value))}
                          style={{width: '80px'}}
                        />
                      </td>
                      <td style={{padding: '5px'}}>
                        <input 
                          type="text" 
                          value={bill.remark || ''}
                          onChange={(e) => handleBillChange(bill.tempId, 'remark', e.target.value)}
                          style={{width: '100%'}}
                        />
                      </td>
                      <td style={{padding: '5px'}}>
                        <button 
                          onClick={() => handleRemoveRecognized(bill.tempId)}
                          style={{color: 'red', border: 'none', background: 'none', cursor: 'pointer'}}
                        >
                          删除
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{marginTop: '15px', textAlign: 'right'}}>
              <button 
                onClick={handleSaveBills}
                style={{
                  padding: '10px 20px', 
                  backgroundColor: '#28a745', 
                  color: 'white', 
                  border: 'none', 
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '16px'
                }}
              >
                保存所有账单
              </button>
            </div>
          </div>
        )}

        {/* 统计图表区域 (切换式布局) */}
        <div style={{marginBottom: '30px'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px'}}>
            <div style={{display: 'flex', gap: '10px'}}>
              <select 
                value={dateRange}
                onChange={(e) => setDateRange(e.target.value)}
                style={{padding: '5px 10px', borderRadius: '4px', border: '1px solid #ddd'}}
              >
                <option value="weekly">近七天</option>
                <option value="monthly">本月</option>
              </select>
              <input 
                type="date" 
                value={queryDate}
                onChange={(e) => setQueryDate(e.target.value)}
                style={{padding: '5px', borderRadius: '4px', border: '1px solid #ddd'}}
              />
            </div>

            <div style={{display: 'flex', gap: '10px'}}>
              <button 
                onClick={() => setChartType('bar')}
                style={{
                  padding: '5px 15px',
                  borderRadius: '20px',
                  border: '1px solid #007bff',
                  backgroundColor: chartType === 'bar' ? '#007bff' : 'white',
                  color: chartType === 'bar' ? 'white' : '#007bff',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                每日趋势
              </button>
              <button 
                onClick={() => setChartType('pie')}
                style={{
                  padding: '5px 15px',
                  borderRadius: '20px',
                  border: '1px solid #007bff',
                  backgroundColor: chartType === 'pie' ? '#007bff' : 'white',
                  color: chartType === 'pie' ? 'white' : '#007bff',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                分类占比
              </button>
            </div>
          </div>

          <div style={{minHeight: '300px'}}>
            {!loading && (
              chartType === 'bar' ? (
                barChartOption && (
                  <ReactECharts 
                    option={barChartOption} 
                    style={{height: '350px'}} 
                    onEvents={{
                      'click': onChartClick
                    }}
                  />
                )
              ) : (
                pieChartOption && (
                  <ReactECharts 
                    option={pieChartOption} 
                    style={{height: '350px'}} 
                  />
                )
              )
            )}
          </div>
        </div>

        {/* 账单明细列表 */}
        <div>
          <h4 style={{margin: '0 0 15px 0', color: '#666'}}>
            {selectedDate ? `${selectedDate} 账单明细` : '所有账单明细'}
          </h4>

          {loading ? (
            <p style={{textAlign: 'center'}}>加载中...</p>
          ) : displayedBills.length === 0 ? (
            <p style={{textAlign: 'center', color: '#666'}}>暂无账单记录</p>
          ) : (
            <div className="bill-list">
              {displayedBills.map(bill => (
                <div key={bill.id} style={{
                  padding: '15px', 
                  borderBottom: '1px solid #eee',
                  display: 'flex', 
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <div style={{fontWeight: 'bold', fontSize: '16px'}}>{bill.title}</div>
                    <div style={{color: '#666', fontSize: '12px', marginTop: '5px'}}>
                      {bill.trade_time} · {bill.category} {bill.merchant ? `· ${bill.merchant}` : ''}
                    </div>
                    {bill.remark && <div style={{color: '#999', fontSize: '12px', marginTop: '2px'}}>{bill.remark}</div>}
                  </div>
                  <div style={{fontWeight: 'bold', fontSize: '18px', color: '#333'}}>
                    ¥{bill.amount}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Bills;
