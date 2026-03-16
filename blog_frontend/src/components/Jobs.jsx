import React, { useState, useEffect, useMemo, useRef } from 'react';
import { getJobs, triggerCrawl, getCrawlResult } from '../api';
import ReactECharts from 'echarts-for-react';

function Jobs() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [crawling, setCrawling] = useState(false);
  const [crawlResults, setCrawlResults] = useState(null); // 爬取结果详情
  const pollTimerRef = useRef(null);
  const [dateRange, setDateRange] = useState('weekly'); // 'weekly' or 'monthly'
  const [date] = useState(() => {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  });
  const [selectedDate, setSelectedDate] = useState(null);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  // 获取所有招聘数据
  const fetchJobs = async () => {
    setLoading(true);
    setError('');
    try {
      // 这里的 date 是查询截止日期，后端会根据 dateRange 返回对应范围的数据
      const response = await getJobs(date, dateRange);
      const newJobs = response.data.jobs || [];
      setJobs(newJobs);
      setHasMore(false);
      // 默认选中查询日期
      setSelectedDate(date);
    } catch (err) {
      console.error('Failed to fetch jobs:', err);
      setError('获取招聘信息失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [date, dateRange]);

  // 处理图表数据
  const chartOption = useMemo(() => {
    if (jobs.length === 0) return null;

    // 1. 生成日期列表
    const days = [];
    if (dateRange === 'weekly') {
      // 近七天
      for (let i = 6; i >= 0; i--) {
        const d = new Date(date);
        d.setDate(d.getDate() - i);
        days.push(d.toISOString().split('T')[0]);
      }
    } else {
      // 本月 (从月初到月末)
      const d = new Date(date);
      const year = d.getFullYear();
      const month = d.getMonth(); // 0-11
      const lastDay = new Date(year, month + 1, 0).getDate(); // 获取当月最后一天
      
      for (let i = 1; i <= lastDay; i++) {
        const dayStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
        days.push(dayStr);
      }
    }

    // 2. 统计每天的职位数量
    const dailyCounts = days.map(day => {
      const count = jobs.filter(j => j.publish_date === day).length;
      return {
        date: day,
        count: count,
        weekday: new Date(day).toLocaleDateString('zh-CN', { weekday: 'short' })
      };
    });

    return {
      title: {
        text: dateRange === 'weekly' ? '近七天招聘职位统计' : '本月招聘职位统计',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          const data = params[0].data;
          return `${data.date} (${data.weekday})<br/>职位数: ${data.value}`;
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
        data: dailyCounts.map(d => dateRange === 'weekly' ? `${d.weekday}\n${d.date.slice(5)}` : d.date.slice(8)),
        axisLabel: {
          interval: dateRange === 'weekly' ? 0 : 'auto',
          rotate: 0
        }
      },
      yAxis: {
        type: 'value',
        name: '数量'
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
          show: dateRange === 'monthly'
        }
      ],
      series: [
        {
          data: dailyCounts.map(d => ({
            value: d.count,
            date: d.date,
            weekday: d.weekday,
            itemStyle: {
              color: d.date === selectedDate ? '#28a745' : '#5470c6'
            }
          })),
          type: 'bar',
          barWidth: dateRange === 'weekly' ? '40%' : '60%',
          label: {
            show: dateRange === 'weekly', // 月度数据太密，不显示数值
            position: 'top',
            formatter: '{c}'
          }
        }
      ]
    };
  }, [jobs, date, selectedDate, dateRange]);

  const onChartClick = (params) => {
    if (params.data && params.data.date) {
      setSelectedDate(params.data.date);
    }
  };

  const handleCrawl = async () => {
    if (crawling) return;
    if (!window.confirm('确定要开始爬取吗？这可能需要一些时间。')) return;

    setCrawling(true);
    setCrawlResults(null);
    try {
      const res = await triggerCrawl();
      if (res.data.message.includes('正在运行')) {
        alert(res.data.message);
        setCrawling(false);
        return;
      }
      // 开始轮询结果
      startPolling();
    } catch (err) {
      console.error('Failed to trigger crawl:', err);
      alert('启动爬虫失败');
      setCrawling(false);
    }
  };

  const startPolling = () => {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    pollTimerRef.current = setInterval(async () => {
      try {
        const res = await getCrawlResult();
        const { running, results, finished_at } = res.data;
        if (!running && finished_at) {
          clearInterval(pollTimerRef.current);
          setCrawling(false);
          setCrawlResults(results);
          fetchJobs(); // 刷新列表
        }
      } catch (e) {
        clearInterval(pollTimerRef.current);
        setCrawling(false);
      }
    }, 3000);
  };

  useEffect(() => {
    return () => { if (pollTimerRef.current) clearInterval(pollTimerRef.current); };
  }, []);

  // 过滤显示
  const displayedJobs = useMemo(() => {
    if (!selectedDate) return jobs;
    return jobs.filter(j => j.publish_date === selectedDate);
  }, [jobs, selectedDate]);

  return (
    <div>
      <div className="card">
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px'}}>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button 
              onClick={() => setDateRange('weekly')} 
              style={{
                padding: '5px 10px',
                cursor: 'pointer',
                backgroundColor: dateRange === 'weekly' ? '#007bff' : '#f0f0f0',
                color: dateRange === 'weekly' ? 'white' : '#333',
                border: '1px solid #ddd',
                borderRadius: '4px'
              }}
            >
              近七天
            </button>
            <button 
              onClick={() => setDateRange('monthly')} 
              style={{
                padding: '5px 10px',
                cursor: 'pointer',
                backgroundColor: dateRange === 'monthly' ? '#007bff' : '#f0f0f0',
                color: dateRange === 'monthly' ? 'white' : '#333',
                border: '1px solid #ddd',
                borderRadius: '4px'
              }}
            >
              本月
            </button>
          </div>
          
          <button 
            onClick={handleCrawl} 
            disabled={crawling}
            style={{
              cursor: 'pointer', 
              backgroundColor: crawling ? '#ccc' : '#28a745', 
              color: 'white', 
              padding: '8px 16px', 
              borderRadius: '4px',
              fontSize: '14px',
              border: 'none'
            }}
          >
            {crawling ? '正在启动...' : '开始爬取'}
          </button>
        </div>

        {/* 爬取结果面板 */}
        {crawlResults && (
          <div style={{ marginBottom: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <strong style={{ fontSize: '14px' }}>上次爬取结果</strong>
              <button onClick={() => setCrawlResults(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#999', fontSize: '16px' }}>✕</button>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: '#e9ecef' }}>
                  <th style={{ padding: '6px 10px', textAlign: 'left', borderBottom: '1px solid #dee2e6' }}>来源</th>
                  <th style={{ padding: '6px 10px', textAlign: 'left', borderBottom: '1px solid #dee2e6' }}>状态</th>
                  <th style={{ padding: '6px 10px', textAlign: 'left', borderBottom: '1px solid #dee2e6' }}>新增</th>
                  <th style={{ padding: '6px 10px', textAlign: 'left', borderBottom: '1px solid #dee2e6' }}>详情</th>
                </tr>
              </thead>
              <tbody>
                {crawlResults.map((r, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
                    <td style={{ padding: '6px 10px' }}>{r.label || '-'}</td>
                    <td style={{ padding: '6px 10px' }}>
                      <span style={{
                        padding: '2px 8px', borderRadius: '4px', fontSize: '12px',
                        background: r.status === 'success' ? '#d4edda' : r.status === 'error' ? '#f8d7da' : '#fff3cd',
                        color: r.status === 'success' ? '#155724' : r.status === 'error' ? '#721c24' : '#856404'
                      }}>
                        {r.status === 'success' ? '✓ 成功' : r.status === 'error' ? '✗ 失败' : '跳过'}
                      </span>
                    </td>
                    <td style={{ padding: '6px 10px', fontWeight: r.new_count > 0 ? 'bold' : 'normal', color: r.new_count > 0 ? '#28a745' : '#666' }}>
                      {r.new_count > 0 ? `+${r.new_count}` : r.status === 'success' ? '0' : '-'}
                    </td>
                    <td style={{ padding: '6px 10px', color: '#666', fontSize: '12px' }}>{r.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {error && <div className="error">{error}</div>}

        {/* 统计图表区域 */}
        <div style={{marginBottom: '30px'}}>
          {!loading && chartOption && (
            <ReactECharts 
              option={chartOption} 
              style={{height: '300px'}} 
              onEvents={{
                'click': onChartClick
              }}
            />
          )}
        </div>

        {/* 职位列表 */}
        <div>
          <h4 style={{margin: '0 0 15px 0', color: '#666'}}>
            {selectedDate ? `${selectedDate} 职位明细` : '所有职位明细'}
          </h4>

          {loading ? (
            <p style={{textAlign: 'center'}}>加载中...</p>
          ) : displayedJobs.length === 0 ? (
            <p style={{textAlign: 'center', color: '#666', padding: '20px'}}>
              暂无招聘信息，请尝试点击“开始爬取”。
            </p>
          ) : (
            <div className="job-list">
              {displayedJobs.map(job => (
                <div key={job.id} style={{
                  padding: '15px', 
                  borderBottom: '1px solid #eee',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '10px'
                }}>
                  <div style={{flex: 1, minWidth: '200px'}}>
                    <h4 style={{margin: '0 0 5px 0'}}>
                      <a href={job.url} target="_blank" rel="noopener noreferrer" style={{textDecoration: 'none', color: '#007bff'}}>
                        {job.title}
                      </a>
                    </h4>
                    <div style={{display: 'flex', gap: '10px', fontSize: '12px', color: '#666'}}>
                      {job.type && <span style={{background: '#f0f0f0', padding: '2px 6px', borderRadius: '4px'}}>{job.type}</span>}
                      {job.dq && <span style={{background: '#f0f0f0', padding: '2px 6px', borderRadius: '4px'}}>{job.dq}</span>}
                    </div>
                  </div>
                  <div style={{fontSize: '14px', color: '#999', whiteSpace: 'nowrap'}}>
                    {job.publish_date}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 分页控制栏 - 已移除 */}
      </div>
    </div>
  );
}

export default Jobs;
