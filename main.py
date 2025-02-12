import os
import sys
from datetime import datetime
import stock_data_reader
import convert_to_json

def main():
    print("=== 股票数据处理系统 ===")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 运行stock_data_reader
        print("\n=== 第一步：读取并处理股票数据 ===")
        stock_data_reader.main()
        
        # 2. 运行convert_to_json
        print("\n=== 第二步：转换数据为JSON格式 ===")
        convert_to_json.main()
        
        print("\n=== 处理完成 ===")
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"\n错误: {str(e)}")
        print("程序异常终止")
        sys.exit(1)

if __name__ == "__main__":
    main() 