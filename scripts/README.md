# Scripts

반복 실행이 필요한 파싱, 정제, CSV 생성 코드를 이 폴더에 둡니다.

## CSV 생성

`data/raw/`의 원본 PDF 2개를 LlamaParse `agentic_plus` tier로 다시 파싱하고, PDF당 clean CSV 하나씩만 생성합니다.

```bash
/opt/anaconda3/bin/python scripts/build_manual_csvs.py
```

산출물:

- `data/processed/stay_manual_clean.csv`
- `data/processed/visa_manual_clean.csv`

기본 실행은 기존 `data/processed/*.csv`를 먼저 지워서 완성 CSV가 위 두 개만 남게 합니다.
