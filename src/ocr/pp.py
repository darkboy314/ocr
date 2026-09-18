import os
from paddleocr import PaddleOCR, PPStructureV3


# start PP-OCR v6 and save result 
def start_ppocr(
    filename: str,
    output_dir: str = "output",
    save_image: bool = True,
    save_json: bool = True,
):
    ocr_pipeline = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            device="gpu",
        )
    pipeline = ocr_pipeline
    result = list(pipeline.predict(filename))
    
    # Save the results to the output directory
    os.makedirs(output_dir, exist_ok=True)
    for res in result:
        res.print()
        res.save_to_img(output_dir + '/img') if save_image else None
        res.save_to_json(output_dir + '/json') if save_json else None
    
    return result


# start PP-Structure v3 and save result 
def start_ppstructure(
    filename: str,
    output_dir: str = "output",
    save_image: bool = True,
    save_json: bool = True,
    save_md: bool = True
):
    ocr_pipeline = PPStructureV3(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            device="gpu",
        )
    pipeline = ocr_pipeline
    result = list(pipeline.predict(filename))
    
    # Save the results to the output directory
    os.makedirs(output_dir, exist_ok=True)
    for res in result:
        res.print()
        res.save_to_img(output_dir + '/img') if save_image else None
        res.save_to_json(output_dir + '/json') if save_json else None
        res.save_to_markdown(output_dir + '/md') if save_md else None
    
    return result