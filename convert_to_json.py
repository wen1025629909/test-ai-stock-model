import pandas as pd
import json
from datetime import datetime

def convert_csv_to_json(csv_file):
    """将CSV数据转换为指定的JSON格式"""
    # 读取CSV文件
    df = pd.read_csv(csv_file, encoding='gbk')
    
    # 将交易日期转换为datetime
    df['交易日期'] = pd.to_datetime(df['交易日期'])
    
    # 获取最新日期的数据
    latest_date = df['交易日期'].max()
    latest_data = df[df['交易日期'] == latest_date]
    
    # 初始化结果列表
    result = []
    
    # 对每只股票处理数据
    for _, row in latest_data.iterrows():
        # 构建股票代码（添加.SH或.SZ后缀）
        symbol = row['股票代码']
        if str(symbol).startswith('6'):
            symbol = f"{symbol}.SH"
        else:
            symbol = f"{symbol}.SZ"
            
        # 构建单个股票的数据结构
        stock_data = {
            "symbol": symbol,
            "date": row['交易日期'].strftime('%Y-%m-%d'),
            "factors": {
                "trend": {
                    "ma_strength": row['均线突破强度'],
                    "momentum_5d": row['日线动量']
                },
                "volume": {
                    "price_vol_corr": row['量价齐升度'],
                    "turnover_rate": row['换手率']
                },
                "volatility": {
                    "atr_rank": -row['ATR'],
                    "swing_stability": -row['振幅稳定性']
                },
                "cap": {
                    "cap_rank": row['市值分位'],
                    "cap_growth_5d": row['市值动量']
                }
            },
            "score": {
                "total": row['综合评分'],
                "group_breakdown": {
                    "trend": row['趋势组得分'],
                    "volume": row['量能组得分'],
                    "volatility": row['波动组得分'],
                    "cap": row['市值组得分']
                }
            },
            "price_data": {
                "open": row['开盘价'],
                "high": row['最高价'],
                "low": row['最低价'],
                "close": row['收盘价'],
                "volume": row['成交量'] / 100  # 转换为手
            }
        }
        
        result.append(stock_data)
    
    # 按综合评分排序
    result.sort(key=lambda x: x['score']['total'], reverse=True)
    
    return result

def main():
    # 获取最新的CSV文件（假设文件名包含日期）
    import glob
    csv_files = glob.glob('top30_stocks_full_data_*.csv')
    if not csv_files:
        print("未找到数据文件")
        return
    
    latest_file = max(csv_files)  # 获取最新的文件
    print(f"处理文件: {latest_file}")
    
    # 转换数据
    json_data = convert_csv_to_json(latest_file)
    
    # 保存为JSON文件
    output_file = latest_file.replace('.csv', '.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"数据已保存到: {output_file}")
    print(f"共转换 {len(json_data)} 只股票的数据")

if __name__ == "__main__":
    main() 