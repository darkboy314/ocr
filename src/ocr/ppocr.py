import os

from paddleocr import PaddleOCR, PPStructureV3


class Ocr:
    def __init__(self):
        self.ocr_pipeline = PaddleOCR(
            device = "gpu",
            use_doc_orientation_classify=False, # 通过 use_doc_orientation_classify 参数指定不使用文档方向分类模型
            use_doc_unwarping=False, # 通过 use_doc_unwarping 参数指定不使用文本图像矫正模型
            use_textline_orientation=False, # 通过 use_textline_orientation 参数指定不使用文本行方向分类模型   
        )
        self.struct_pipeline = PPStructureV3(
            paddlex_config="PP-StructureV3.yaml" # 配置文件
        )
        return


    def start_ocr(
        self,
        filename: str,
        isfileoutputenabled: bool,
        output_dir: str = "output",
    ):
        pipeline = self.pipeline
        result = pipeline.predict(filename)
        
        # if file output is enable, then output image and json file
        if isfileoutputenabled:
            os.makedirs(output_dir, exist_ok=True)
            for res in result:
                res.print()
                res.save_to_img(output_dir)
                res.save_to_json(output_dir)
        
        return result

    def start_struct_ocr(
        self,
        filename: str,
        isfileoutputenabled: bool,
        output_dir: str = "output",
    ):
        pipeline = self.struct_pipeline
        result = pipeline.predict(filename)

        # if file output is enable, then output image and json file
        if isfileoutputenabled:
            os.makedirs(output_dir, exist_ok=True)
            for res in result:
                res.print()
                res.save_to_img(output_dir)
                res.save_to_json(output_dir)
        
        return result

    