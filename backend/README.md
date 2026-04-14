# DS200 Backend Skeleton

Bo khung backend nay duoc tao de ban co the cam nhanh code crawler khi nhan tu teammate.

## Cau truc thu muc

- `src/app/config`: Quan ly bien moi truong va settings.
- `src/app/database`: Ket noi DB va model quan he.
- `src/app/services`: Noi dat code crawl, transcribe, llm, storage.
- `src/scripts`: Script chay tay (bootstrap DB, test ket noi).

## Quy uoc S3

- Transcript key: `transcripts/[product_id]/[video_id]_transcript.txt`
- Comments key: `comments/[product_id]/[video_id]_comments.csv`
- Cau hinh 2 bucket rieng trong env:
  - `AWS_S3_TRANSCRIPTS_BUCKET`
  - `AWS_S3_COMMENTS_BUCKET`

## Lenh craw dữ liệu

```bash
cd DS200_Big_Data/backend
python -m venv DS200_env
source DS200_env/Scripts/activate
pip install -r requirements.txt
python -m src.scripts.bootstrap_db # tạo schema db
python -m src.scripts.run_link_crawler # craw link
python -m src.scripts.run_spec_crawler # scrape giá trị của các thuộc tính sản phẩm
python -m src.scripts.load_products_to_db --truncate
```

