from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from contextlib import closing
import sqlite3
import logging
import argparse

def load_info(db, table):
    if not table:
        table = db.stem
    with closing(sqlite3.connect(db)) as con:
        con.row_factory = sqlite3.Row
        return con.execute(f"SELECT visit_id, url, accept_found, banner_found, css_id, "
        f"accept_cta, banner_selector, cta_list FROM {table}").fetchall()

def label_image(image, data):
    with Image.open(image) as image:
        font = ImageFont.truetype('Arial.ttf', 16)
        xo, yo = 10, 10
        to_draw = []
        to_draw.append({'text': data['url'], 'xy': (xo, yo), 'fill': (0,0,0)})
        yo = yo + font.getsize(to_draw[-1]['text'])[1] + 10
        to_draw.append({'text': 'ACCEPT FOUND' if data['accept_found'] else 'ACCEPT NOT FOUND',
                        'xy': (xo + 10, yo),
                        'fill': (0,255,0) if data['accept_found'] else (255,0,0)})
        to_draw.append({'text': 'BANNER FOUND' if data['banner_found'] else 'BANNER NOT FOUND',
                        'xy': (xo + 210, yo),
                        'fill': (0,255,0) if data['banner_found'] else (255,0,0)})
        yo = yo + font.getsize(to_draw[-1]['text'])[1] + 10
        to_draw.append({'text': f'css_id: {data["css_id"]}', 'xy': (xo, yo), 'fill': (0,0,0)})
        to_draw.append({'text': f'banner_selector: {data["banner_selector"]}', 'xy': (xo + 500, yo), 'fill': (0,0,0)})
        yo = yo + font.getsize(to_draw[-1]['text'])[1] + 10
        to_draw.append({'text': f'accept_cta: {data["accept_cta"]}', 'xy': (xo, yo), 'fill': (0,0,0)})
        to_draw.append({'text': f'cta_list: {data["cta_list"]}', 'xy': (xo + 500, yo), 'fill': (0,0,0)})
        yo = yo + font.getsize(to_draw[-1]['text'])[1] + 10

        x, y = image.size
        y += yo
        new = Image.new('RGBA', (x,y), (255,255,255,255))
        draw = ImageDraw.Draw(new)
        for text in to_draw:
            draw.text(font=font, **text)
        new.paste(image, (0,yo))
        return new

def process_images(img_dir, db, table):
    data = load_info(db, table)
    out_dir = img_dir.joinpath('labelled/')
    out_dir.mkdir()
    num = 0
    for row in data:
        visit_id = row['visit_id']
        image = list(img_dir.glob(f"{visit_id}*-full.png"))
        if image:
            if len(image) > 1:
                logging.error(f"More than one screenshot found for visit_id {visit_id}")
            image = image[0]
            name = ""
            if row['accept_found']:
                name += 'accept_found-'
            elif row['banner_found']:
                name += 'banner_found-'
            newimg = label_image(image, row)
            newimg.save(out_dir.joinpath(f"{name}{visit_id}.png"))
            logging.info(f"Labelled screenshot of visit_id {visit_id}")
            num += 1
        else:
            logging.error(f"No screenshot found for visit_id {visit_id}")
    logging.info(f"Successfully labelled {num} screenshots.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Label screenshots with parsed log results.')
    parser.add_argument('db', type=Path)
    parser.add_argument('img_dir', type=Path)
    parser.add_argument('--table', type=ascii)
    args = parser.parse_args()

    process_images(args.img_dir, args.db, args.table)
