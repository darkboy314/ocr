import ocr, preprocess, report


def main() -> None:
    # preprocessing
    preprocess.run_pipeline()
    
    # start processing file
    ocr.process_files(
        root_dir="input/Final_Algorithm",
        output_dir="output",
        keyword=r"^(?!.*CS).*Maintenance Report.*\.pdf$", # 正则表达式，筛选Maintenance Report但是不包含充电桩的Report
    )
    
    
    return

if __name__ == "__main__":
    main()