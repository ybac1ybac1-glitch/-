from data import get_stock_data


def main():

    print("======================")
    print("威科夫A股盘后选股系统")
    print("======================")

    print("正在获取股票数据...")

    df = get_stock_data()

    print("数据获取完成")

    print(df.head())


if __name__ == "__main__":
    main()