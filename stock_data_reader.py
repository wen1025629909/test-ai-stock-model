import pandas as pd
import os
import numpy as np
from scipy import stats

# 设定数据文件夹路径
data_path = './data/2025-02'

# 读取文件夹中的CSV文件
def read_stock_data(folder_path):
    """读取所有股票最近76天的数据"""
    all_data = []
    
    # 获取文件夹中所有的CSV文件
    csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    total_files = len(csv_files)
    
    print(f"开始读取 {total_files} 个文件的最近76天数据...")
    
    # 首先找到所有文件中的最新日期
    latest_date = None
    for file in csv_files[:100]:  # 取样100个文件来确定最新日期
        try:
            df = pd.read_csv(os.path.join(folder_path, file),
                           encoding='gbk',
                           usecols=['交易日期'],
                           skiprows=1)
            df['交易日期'] = pd.to_datetime(df['交易日期'], errors='coerce')
            max_date = df['交易日期'].max()
            if latest_date is None or (pd.notna(max_date) and max_date > latest_date):
                latest_date = max_date
        except:
            continue
    
    if latest_date is None:
        print("错误：无法确定最新交易日期")
        return None
    
    # 计算76个交易日前的起始日期（考虑到周末，取120天前）
    start_date = latest_date - pd.Timedelta(days=120)
    print(f"数据日期范围: {start_date.date()} 至 {latest_date.date()}")
    
    for i, file in enumerate(csv_files, 1):
        file_path = os.path.join(folder_path, file)
        try:
            # 读取文件
            df = pd.read_csv(file_path, 
                           encoding='gbk',
                           names=['股票代码', '股票名称', '交易日期', '开盘价', 
                                 '最高价', '最低价', '收盘价', '前收盘价',
                                 '成交量', '成交额', '流通市值', '总市值'],
                           skiprows=1)
            
            # 转换日期
            df['交易日期'] = pd.to_datetime(df['交易日期'], errors='coerce')
            
            # 只保留指定日期范围的数据
            df = df[df['交易日期'] >= start_date]
            df = df[df['交易日期'] <= latest_date]
            
            # 将价格相关列转换为浮点数
            numeric_columns = ['开盘价', '最高价', '最低价', '收盘价', '前收盘价', 
                             '成交量', '成交额', '流通市值', '总市值']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 跳过标题行（如果存在）
            df = df[df['交易日期'].notna()]
            
            # 只保留最近76个交易日的数据
            df = df.sort_values('交易日期', ascending=False).head(76)
            
            if not df.empty:
                df['文件名'] = file.replace('.csv', '')
                all_data.append(df)
            
            # 显示进度
            if i % 100 == 0 or i == total_files:
                print(f"已处理 {i}/{total_files} 个文件 ({(i/total_files*100):.1f}%)")
            
        except Exception as e:
            print(f"读取文件 {file} 时出错: {str(e)}")
    
    if all_data:
        print("\n合并数据...")
        combined_data = pd.concat(all_data, ignore_index=True)
        
        # 按股票代码和日期排序
        print("排序数据...")
        combined_data = combined_data.sort_values(['股票代码', '交易日期'])
        
        print(f"\n数据读取完成:")
        print(f"总记录数: {len(combined_data)}")
        print(f"股票数量: {combined_data['股票代码'].nunique()}")
        print(f"日期范围: {combined_data['交易日期'].min().date()} 至 {combined_data['交易日期'].max().date()}")
        print(f"每只股票的平均交易日数: {len(combined_data)/combined_data['股票代码'].nunique():.1f}")
        
        return combined_data
    else:
        return None

def calculate_z_score(series):
    """计算Z值"""
    return (series - series.mean()) / series.std()

def calculate_adjusted_price(group):
    """计算复权价格"""
    # 按日期升序排序
    group = group.sort_values('交易日期')
    
    # 计算日涨跌幅
    group['涨跌幅'] = group['收盘价'] / group['前收盘价'] - 1
    
    # 计算复权因子（从后往前累乘）
    group['复权因子'] = (1 + group['涨跌幅'][::-1]).cumprod()[::-1]
    
    # 计算复权价格
    group['开盘价_后复权'] = group['开盘价'] * group['复权因子']
    group['最高价_后复权'] = group['最高价'] * group['复权因子']
    group['最低价_后复权'] = group['最低价'] * group['复权因子']
    group['收盘价_后复权'] = group['收盘价'] * group['复权因子']
    
    return group

def calculate_indicators(df):
    """计算各项技术指标"""
    results = []
    
    # 按股票代码分组计算复权价格
    print("计算复权价格...")
    df = df.groupby('股票代码', group_keys=False).apply(calculate_adjusted_price)
    
    # 对每个交易日期分别计算市值分位
    print("计算市值分位...")
    def calculate_market_cap_percentile(group):
        """计算市值分位数"""
        group = group.copy()
        group['市值分位'] = group['流通市值'].rank(method='min') / len(group)
        return group
    
    # 按日期分组计算市值分位
    df = df.groupby('交易日期', group_keys=False).apply(calculate_market_cap_percentile)
    
    # 使用复权价格计算指标
    print("计算技术指标...")
    for code, group in df.groupby('股票代码'):
        # 确保数据按交易日期排序
        group = group.sort_values('交易日期')
        
        # 1. 趋势类因子（使用复权价格）
        group['MA5'] = group['收盘价_后复权'].rolling(window=5, min_periods=5).mean()
        group['MA10'] = group['收盘价_后复权'].rolling(window=10, min_periods=10).mean()
        group['MA20'] = group['收盘价_后复权'].rolling(window=20, min_periods=20).mean()
        
        group['均线突破强度'] = (group['收盘价_后复权'] - group['MA20']) / (group['MA20'] * 0.01)
        group['三线开花'] = (group['MA5'] > group['MA10']) & (group['MA10'] > group['MA20'])
        group['日线动量'] = group['收盘价_后复权'] / group['收盘价_后复权'].shift(5) - 1
        group['20日最高价'] = group['最高价_后复权'].rolling(window=20, min_periods=20).max()
        group['高低通道突破'] = group['收盘价_后复权'] > group['20日最高价']
        
        # 2. 量能类因子
        group['量价齐升度'] = group['成交量'].rolling(5).corr(group['收盘价_后复权'])
        group['换手率'] = group['成交量'] / group['流通市值']
        
        # 3. 波动类因子（使用复权价格）
        group['TR1'] = group['最高价_后复权'] - group['最低价_后复权']
        group['TR2'] = abs(group['最高价_后复权'] - group['收盘价_后复权'].shift(1))
        group['TR3'] = abs(group['最低价_后复权'] - group['收盘价_后复权'].shift(1))
        group['TR'] = pd.concat([group['TR1'], group['TR2'], group['TR3']], axis=1).max(axis=1)
        group['ATR'] = group['TR'].rolling(window=14).mean()
        
        group['日振幅'] = group['最高价_后复权'] / group['最低价_后复权']
        group['振幅稳定性'] = group['日振幅'].rolling(window=10).std()
        
        # 4. 市值动量
        group['市值动量'] = group['流通市值'] / group['流通市值'].shift(5)
        
        results.append(group)
    
    result_df = pd.concat(results, ignore_index=True)
    
    # 对每个交易日期分别处理
    print("计算标准化指标...")
    final_results = []
    for date in result_df['交易日期'].unique():
        date_mask = result_df['交易日期'] == date
        date_data = result_df[date_mask].copy()
        
        # 计算各项指标的Z值
        indicators = {
            '均线突破强度': '均线突破强度_Z',
            '日线动量': '日线动量_Z',
            '量价齐升度': '量价齐升度_Z',
            '换手率': '换手率_Z',
            'ATR': 'ATR_Z',
            '振幅稳定性': '振幅稳定性_Z',
            '市值动量': '市值动量_Z'
        }
        
        for orig_col, z_col in indicators.items():
            if len(date_data[orig_col].dropna()) > 0:  # 确保有足够的数据计算Z值
                date_data[z_col] = (date_data[orig_col] - date_data[orig_col].mean()) / date_data[orig_col].std()
            else:
                date_data[z_col] = 0  # 如果没有足够的数据，设置为0
        
        # 波动因子方向修正
        date_data['ATR_Z'] = -date_data['ATR_Z']
        date_data['ATR_Z'] = np.clip(date_data['ATR_Z'], -3, 3)
        
        date_data['振幅稳定性_Z'] = -date_data['振幅稳定性_Z']
        date_data['振幅稳定性_Z'] = np.clip(date_data['振幅稳定性_Z'], -3, 3)
        
        # 市值因子处理规范
        date_data['市值分位_Z'] = date_data['市值分位'].apply(
            lambda x: stats.norm.ppf(x) if 0 < x < 1 else 0
        )
        
        # 计算组得分
        date_data['趋势组得分'] = (date_data['均线突破强度_Z'] + date_data['日线动量_Z']) / 2
        date_data['量能组得分'] = (date_data['量价齐升度_Z'] + date_data['换手率_Z']) / 2
        date_data['波动组得分'] = (date_data['ATR_Z'] + date_data['振幅稳定性_Z']) / 2
        date_data['市值组得分'] = (date_data['市值分位_Z'] + date_data['市值动量_Z']) / 2
        
        # 计算综合评分
        date_data['综合评分'] = (
            date_data['趋势组得分'] * 0.4 +
            date_data['量能组得分'] * 0.3 +
            date_data['波动组得分'] * 0.2 +
            date_data['市值组得分'] * 0.1
        )
        
        final_results.append(date_data)
    
    result_df = pd.concat(final_results, ignore_index=True)
    print("计算完成")
    
    return result_df

def format_preview_data(df):
    """格式化数据以便更好地预览"""
    # 选择要显示的列（只包含确定存在的列）
    preview_df = df[['股票代码', '股票名称', '交易日期', 
                     '开盘价_后复权', '最高价_后复权', '最低价_后复权', '收盘价_后复权',
                     '成交量', '成交额', '流通市值', '总市值',
                     '趋势组得分', '量能组得分', '波动组得分', '市值组得分', '综合评分']]
    
    # 格式化数值列
    for col in preview_df.columns:
        if col not in ['股票代码', '股票名称', '交易日期']:
            preview_df[col] = preview_df[col].round(3)
    
    return preview_df

def main():
    # 读取数据
    df = read_stock_data(data_path)

    if df is not None:
        # 计算指标
        df_with_indicators = calculate_indicators(df)
        
        # 获取最新交易日期
        latest_date = df_with_indicators['交易日期'].max()
        
        # 获取最新日期的前30名股票代码
        latest_data = df_with_indicators[df_with_indicators['交易日期'] == latest_date]
        top_30_stocks = latest_data.nlargest(30, '综合评分')['股票代码'].unique()
        
        # 获取这30只股票的所有历史数据
        top_30_data = df_with_indicators[df_with_indicators['股票代码'].isin(top_30_stocks)]
        
        # 按股票代码和日期排序
        top_30_data = top_30_data.sort_values(['股票代码', '交易日期'])
        
        # 选择要保存的列
        columns_to_save = [
            # 基础信息
            '股票代码', '股票名称', '交易日期', 
            # 价格数据
            '开盘价', '最高价', '最低价', '收盘价', '前收盘价',
            '开盘价_后复权', '最高价_后复权', '最低价_后复权', '收盘价_后复权',
            # 成交数据
            '成交量', '成交额', '流通市值', '总市值',
            # 趋势指标
            'MA5', 'MA10', 'MA20', '均线突破强度', '三线开花', '日线动量', '高低通道突破',
            # 量能指标
            '量价齐升度', '换手率',
            # 波动指标
            'ATR', '振幅稳定性',
            # 市值指标
            '市值分位', '市值动量',
            # Z值
            '均线突破强度_Z', '日线动量_Z', '量价齐升度_Z', '换手率_Z',
            'ATR_Z', '振幅稳定性_Z', '市值分位_Z', '市值动量_Z',
            # 得分
            '趋势组得分', '量能组得分', '波动组得分', '市值组得分', '综合评分'
        ]
        
        # 保存完整结果
        output_file = f'top30_stocks_full_data_{latest_date.strftime("%Y%m%d")}.csv'
        top_30_data[columns_to_save].to_csv(output_file, index=False, encoding='gbk')
        print(f"\nTop30股票的完整数据已保存到: {output_file}")
        
        # 显示最新日期的排名情况
        print(f"\n最新交易日期 {latest_date.date()} 的Top30股票：")
        latest_top_30 = latest_data[latest_data['股票代码'].isin(top_30_stocks)].sort_values('综合评分', ascending=False)
        print(latest_top_30[['股票代码', '股票名称', '综合评分', '趋势组得分', 
                            '量能组得分', '波动组得分', '市值组得分']].to_string())
        
        # 输出一些统计信息
        print("\n数据统计：")
        print(f"数据日期范围: {top_30_data['交易日期'].min().date()} 至 {top_30_data['交易日期'].max().date()}")
        print(f"每只股票的平均交易日数: {len(top_30_data)/30:.1f}")
        
    else:
        print("没有读取到任何数据")

if __name__ == "__main__":
    main() 