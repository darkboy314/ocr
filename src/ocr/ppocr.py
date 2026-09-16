import os
from paddleocr import PPStructureV3


class Ocr:
    def __init__(self):
        self.struct_pipeline = PPStructureV3(
            paddlex_config="PP-StructureV3.yaml" # 配置文件
        )
        return

    def start_ocr(
        self,
        filename: str,
        output_dir: str = "output",
        save_image: bool = True,
        save_json: bool = True,
        save_markdown: bool = True,
    ):
        pipeline = self.struct_pipeline
        result = list(pipeline.predict(filename))
        
        # Save the results to the output directory
        os.makedirs(output_dir, exist_ok=True)
        for res in result:
            res.print()
            res.save_to_img(output_dir + '/img') if save_image else None
            res.save_to_json(output_dir + '/json') if save_json else None
            res.save_to_markdown(output_dir + '/md') if save_markdown else None
        
        return result

    