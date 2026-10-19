# cad-reverse

두 패널짜리 도면 이미지를 색(hue)으로 나눠 **레이어별 도형**으로 분해하고, 그 결과를 GDS와 DXF를 거쳐 **DWG**로 저장하는 스크립트 모음.

> 근사치다. 사진에는 레이어 정보가 없어서 색과 위치로 추정한 결과이고, 파운드리 설계 규칙이나 DRC 검사를 거치지 않았다. 축척은 패널 폭 45 µm 표기를 기준으로 가정했다.

## 파이프라인

```
도면 이미지(PNG)
  └─ make_layers_photo2.py   색 분류 → 레이어별 사각형/원 추출
       ├─ <prefix>.gds           GDS (셀 PIXEL_A / SENSOR_B, 레이어 1~8, 21~25)
       ├─ <prefix>.dxf           DXF (레이어 이름 A_YELLOW … B_BLOCK)
       ├─ <prefix>_gds_map.txt   GDS 레이어 번호 ↔ 이름, 도형 수
       ├─ <prefix>_overlay_check.png   추출 박스를 원본 위에 겹쳐 보기
       └─ <prefix>_geom.pkl      중간 좌표 (재사용용)
  ├─ dxf_to_dwg.sh           DXF → DWG (ODA File Converter, ACAD2018)
  └─ render_photo2_by_layer.py  레이어별 미리보기 PNG
```

**출력 형태 참고:** 결과는 **DWG 한 파일 안에 레이어별로 나뉜** 구조다. 레이어마다 DWG 파일을 따로 만들지는 않는다. 레이어별 DWG 분리는 아직 구현되지 않았다.

## 설치

1. Python 3.10 이상에서 패키지 설치
   ```bash
   python3 -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt
   ```
2. ODA File Converter 설치 (DWG 쓰기에 필요)
   - https://www.opendesign.com/guestfiles/oda_file_converter (Linux x64 DEB/RPM/AppImage)
   - 사용 조건은 ODA 측에서 직접 확인한다. 이 저장소에는 바이너리를 넣지 않았다.
   - Linux에서 번들 Qt가 offscreen 플러그인을 거부하면 시스템 Qt6 라이브러리를 `LD_LIBRARY_PATH`와 `QT_PLUGIN_PATH`로 지정한다.

## 실행

```bash
# 1) 도면 이미지 분해 (입력은 두 패널짜리 PNG)
python make_layers_photo2.py my_figure.png out/my_figure

# 2) DXF → DWG
ODA_CONVERTER=/path/to/ODAFileConverter ./dxf_to_dwg.sh out/my_figure.dxf out/dwg

# 3) 레이어별 미리보기
python render_photo2_by_layer.py out/my_figure.gds out/my_figure_by_layer.png
```

`ODAFileConverter`가 PATH에 있으면 `ODA_CONVERTER`는 생략해도 된다.

## 다른 이미지에 쓸 때 주의

- `make_layers_photo2.py`의 `A_BOX`, `B_BOX` 픽셀 좌표는 **예시 사진에 맞춰진 값**이다. 다른 이미지는 좌표를 새로 잡아야 한다. `_overlay_check.png`로 박스 위치를 먼저 확인한다.
- 색 분류 기준(`classify_a`의 hue 구간)도 이미지마다 다를 수 있다.
- 사진 기반이라 치수는 참고용이다.

## 예시 파일 (`examples/`)

| 파일 | 설명 |
|---|---|
| `photo2_layers.dwg` | 예시 결과 DWG (ACAD2018) |
| `photo2_layers.gds` | 예시 GDS |
| `photo2_layers_gds_map.txt` | GDS 레이어 번호와 이름 |
| `photo2_layers_preview.png` | 전체 미리보기 |
| `photo2_layers_by_layer.png` | 레이어별 미리보기 |

## 파일

- `make_layers_photo2.py` — 메인 분해 스크립트
- `dxf_to_dwg.sh` — DXF → DWG 변환 래퍼
- `render_photo2_by_layer.py` — 레이어별 미리보기
- `render_photo2_preview.py` — GDS 전체 미리보기
- `requirements.txt` — 파이썬 의존성 (테스트에 쓴 버전으로 고정)
