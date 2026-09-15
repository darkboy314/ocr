import re
from collections import defaultdict


# example_path = "./AT0484_Wang Fai Motors/Operation Data/M01/AT0484 - 06 - Form E2 - Maintenance Report (EV)_YX1161_M01_Dec2023.pdf"

class TextProcess:
    def process_info(self, raw_info:list) -> dict:
        path = []
        text_context = []
        
        # classify raw data
        for info in raw_info:
            path.append(info["input_path"])
            text_context.append(info)

        # merge values with the same key
        merged = defaultdict(list)
        for k, v in zip(path, text_context):
            merged[k].append(v)
            
        return merged


    def extract_info_from_data_test(self, raw_info:dict) -> list:
        
        pass


    def extract_info_from_data(self, raw_info:dict) -> list:
        agree_numbers = []
        recipients = []
        veh_reg_numbers = []
        veh_models = []
        service_routes = []
        meter_readings = []
        maintenance_companies = []
        maintenance_dates_from = []
        maintenance_dates_to = []
        down_times = []
        maintenance_types = []
        reasons = []
        accident_dates = []
        accident_locations = []
        accident_descriptions = []
        accident_causes = []
        maintenance_lists = []
        maintenance_costs = []
        total_costs = []

        def pages_from_context(context):
            if isinstance(context, dict):
                return [context]
            return context if isinstance(context, list) else []

        def page_texts(context):
            texts = []
            for page in pages_from_context(context):
                texts.extend(str(text).strip() for text in page.get("rec_texts", []))
            return texts

        def find_index(texts, pattern, start=0):
            for index in range(start, len(texts)):
                if re.search(pattern, texts[index], re.IGNORECASE):
                    return index
            return -1

        label_pattern = (r"資助協議編號|受資助者名稱|車牌號碼|車輛型號|服務路線|"
                         r"Odometer reading at|維修時里程表讀數/公里|維修公司名稱|維修日期和時間|停運時間/小時|"
                         r"維修類型|事故發生日期及時間|事故地點、經過及當時採取嘅對應措施|事故原因|維修項目|總維修費用|"
                         r"Maintenance|Service route|Operation down time|"
                         r"Date & time|Location|Cause of incident|Total maintenance|"
                         r"^from$|^to$|Form C2|2020/9")

        def next_value(texts, pattern, start=0):
            label_index = find_index(texts, pattern, start)
            if label_index < 0 or label_index + 1 >= len(texts):
                return ""
            value = texts[label_index + 1].strip()
            return "" if re.search(label_pattern, value, re.IGNORECASE) else value

        def value_at(texts, index):
            if 0 <= index < len(texts):
                return texts[index]
            return ""

        def table_data(texts):
            table_start = find_index(texts, r"維修項目|Maintenance items")
            total_index = find_index(texts, r"總維修費用|Total maintenance cost", table_start + 1)
            if table_start < 0:
                return [""] * 20, [], ""
            if total_index < 0:
                total_index = len(texts) 
            table_texts = texts[table_start + 1:total_index]
            number_pattern = re.compile(r"^\d{1,2}\s*[.]")
            starts = [index for index, text in enumerate(table_texts)
                      if number_pattern.match(text)]
            items = [""] * 20
            costs = []
            ignored = {"口", "日", "☑", "□", "更换", "更換"}
            pending_item = ""
            for row_index, row_start in enumerate(starts[:20]):
                row_end = starts[row_index + 1] if row_index + 1 < len(starts) else len(table_texts)
                row = table_texts[row_start:row_end]
                item_values = [pending_item] if pending_item else []
                row_cost = ""
                cost_seen = False
                trailing_values = []
                for text in row:
                    text = re.sub(r"^\d{1,2}\s*[.]\s*", "", text).strip()
                    if not text or text in ignored:
                        continue
                    if re.fullmatch(r"\d+(?:[.]\d+)?", text):
                        row_cost = text
                        cost_seen = True
                    elif not re.search(r"修理|Repaired|費用|Cost", text, re.IGNORECASE):
                        if cost_seen:
                            trailing_values.append(text)
                        else:
                            item_values.append(text)
                items[row_index] = " ".join(item_values)
                costs.append(row_cost)
                pending_item = " ".join(trailing_values)
            total = value_at(texts, total_index + 1)
            return items, costs, total

        for context in raw_info.values():
            texts = page_texts(context)
            agreement_index = find_index(texts, r"資助協議編號|Subsidy Agreement No")
            recipient_index = find_index(texts, r"受資助者名稱|Subsidy recipient name")
            vehicle_index = find_index(texts, r"車輛型號|Vehicle model")
            date_values = [match.group(0) for text in texts
                           for match in [re.search(r"\d{1,4}[-/]\d{1,2}[-/]\d{1,4}", text)]
                           if match]
            items, costs, total = table_data(texts)
            agree_numbers.append(next_value(texts, r"資助協議編號|Subsidy Agreement No"))
            recipients.append(next_value(texts, r"受資助者名稱|Subsidy recipient name"))
            veh_reg_numbers.append(value_at(texts, vehicle_index + 1))
            veh_models.append(value_at(texts, vehicle_index + 2))
            service_routes.append(next_value(texts, r"服務路線|Service route"))
            meter_readings.append(next_value(texts, r"^Odometer reading at$"))
            maintenance_companies.append(next_value(texts, r"維修公司名稱|Maintenance company name"))
            maintenance_dates_from.append(date_values[0] if date_values else "")
            maintenance_dates_to.append(date_values[1] if len(date_values) > 1 else "")
            down_times.append(next_value(texts, r"停運時間/小時|Operation down time/hour"))
            maintenance_types.append("")
            reasons.append("")
            accident_dates.append(next_value(texts, r"事故發生日期及時間|Date & time"))
            accident_locations.append(next_value(texts, r"事故地點|Location, course"))
            accident_descriptions.append(next_value(texts, r"事故地點|Location, course"))
            accident_causes.append(next_value(texts, r"事故原因|Cause of incident"))
            maintenance_lists.append(items)
            maintenance_costs.append(costs)
            total_costs.append(total)

        return list(zip(agree_numbers, recipients, veh_reg_numbers, veh_models, service_routes, meter_readings,
                        maintenance_companies, maintenance_dates_from, maintenance_dates_to, down_times,
                        maintenance_types, reasons, accident_dates, accident_locations, accident_descriptions,
                        accident_causes, maintenance_lists, maintenance_costs, total_costs))


    def extract_info_from_path(self, raw_info:dict) -> list:
        codes = []
        companies = []
        types = []
        car_numbers = []
        dates = []

        pattern = r"^\.\/([A-Z0-9]+)_([^/]+)\/.*\((EV)\)_(\w+)_[^/]*_([A-Za-z]{3}\d{4})"

        for path, context in raw_info.items():
            match = re.search(pattern, path)
            if match:
                code = match.group(1)   # "AT0484"
                company = match.group(2)   # "Wang Fai Motors"
                type = match.group(3)   # "Dec2023"
                car_number = match.group(4)   # "YX1161"
                date = match.group(5)   # "Dec2023"

                codes.append(code)
                companies.append(company)
                types.append(type)
                car_numbers.append(car_number)
                dates.append(date)

        zipped = zip(codes, companies, types, car_numbers, dates)
        return list(zipped)


