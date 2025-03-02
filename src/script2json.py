import re
import random
import json
from logger import logger
from app.videoproject.parsers import parse_media_line

def parse_script(script: str) -> dict:
    MUSIC_LIST = ["track_random_1", "track_random_2", "track_random_3"]    
    result = {
        "category": None,
        "title": None,
        "keyword": [],
        "src": None,
        "description": None,
        "unique_id": None,
        "ads": None,
        "playlist": [],
        "test": False,
        "speaker": None,
        "upload": ["youtube"],
        "thumbnail": None,
        "background_music": None,
        "video": [],
        "is_vertical": False
    }
    
    lines = script.strip().split('\n')
    re_break = re.compile(r'^<break(?:=(\d+))?>')
    re_music = re.compile(r'^<music(?:=(\d+))?>')
    
    # Buffers cho bài chính
    main_media_buffer = []  # Lưu các dòng media chưa flush
    main_text_buffer = []   # Lưu các text elements đã đọc sau media
    
    global_bg = None
    first_line_processed = False
    
    def flush_main_segment():
        nonlocal main_media_buffer, main_text_buffer, result
        # Chỉ flush nếu có ít nhất một media được đọc
        if main_media_buffer:
            if not main_text_buffer:
                main_text_buffer.append("")  # Tránh trường hợp không có text
            segment = {
                "media_clips": main_media_buffer,
                "content": main_text_buffer,
            }
            result["video"].append(segment)
            main_media_buffer = []
            main_text_buffer = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('-'):
            continue

        line = re.sub(r'(?<!^)\s*-\s*', '-', line)
        
        # Dòng đầu tiên: "Category: Title"
        if not first_line_processed:
            if ':' in line:
                parts = line.split(':', 1)
                result["category"] = parts[0].strip()
                result["title"] = parts[1].strip()
            else:
                result["category"] = line
            first_line_processed = True
            continue
        
        # Xử lý metadata của bài chính (không thuộc nội dung segment)
        if line.startswith('+'):
            ln = line.lstrip('+').strip()
            if ':' in ln:
                key, val = ln.split(':', 1)
                key = key.strip()
                val = val.strip()
                result[key] = val       
            continue
        if line.startswith('#'):
            result["keyword"] = line.lstrip('#').strip()
            continue
        if line.startswith('$'):
            result["src"] = line.lstrip('$').strip()
            continue

        if line.startswith('http://') or line.startswith('https://'):
            if main_text_buffer:
                flush_main_segment()
            main_media_buffer.append(parse_media_line(line))
        else:
            # Dòng này là text (hoặc lệnh <break>, <music>)
            m_b = re_break.match(line)
            m_m = re_music.match(line)
            if m_b:
                pass  # Do nothing, handled in media flush
            elif m_m:
                pass
            else:
                main_text_buffer.append(line)
    
    # Kết thúc bài chính: nếu còn media chưa flush, flush segment
    if main_media_buffer:
        flush_main_segment()

    # Nếu global background music chưa được set, chọn ngẫu nhiên
    if global_bg is None:
        global_bg = random.choice(MUSIC_LIST)

    
    return result

# Demo: chuyển dict sang JSON để kiểm tra kết quả

def test_parse_script(): 
    logger.info('[x] Testing parse_script')
    # read text from file
    with open('sample2.txt', 'r') as file:
        script = file.read()

    # parse script
    result = parse_script(script)
    logger.info(f'[x] Parsed result: {json.dumps(result, ensure_ascii=False, indent=4)}')
    # dump to file sample2.json
    with open('sample2.json', 'w') as file:
        file.write(json.dumps(result, ensure_ascii=False, indent=4))
    logger.info('[x] Result saved to sample2.json')

if __name__ == "__main__":
    test_parse_script()