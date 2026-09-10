from paddleocr import PaddleOCR 
from collections import defaultdict


class Ocr:
    def __init__(self):
        self.pipeline = PaddleOCR(
            device = "gpu",
            use_doc_orientation_classify=False, # 通过 use_doc_orientation_classify 参数指定不使用文档方向分类模型
            use_doc_unwarping=False, # 通过 use_doc_unwarping 参数指定不使用文本图像矫正模型
            use_textline_orientation=False, # 通过 use_textline_orientation 参数指定不使用文本行方向分类模型   
        )
        return


    def start_ocr(self, filename:str, isfileoutputenable:bool):
        pipeline = self.pipeline
        result = pipeline.predict(filename)
        
        # if file output is enable, then output image and json file
        if isfileoutputenable:
            for res in result:
                res.print()
                res.save_to_img("output")
                res.save_to_json("output")
        
        return result
    
    
    def extract_info(self, raw_info:list) -> dict:
        path = []
        text_context = []
        
        # classify raw data
        for info in raw_info:
            path.append(info.input_path)
            text_context.append(info.rec_texts)
        
        # merge into a dict
        dict = dict(zip(path, text_context))
        
        # merge values with the same key
        merged = defaultdict(list)
        for k, v in dict:
            merged[k].append(v)
            
        return merged
    