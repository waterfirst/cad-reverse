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

**레이어 색:** 레이어마다 서로 다른 AutoCAD 색(ACI)을 준다. `A_*`는 사진의 색 분류와 같은 색(YELLOW=2, RED=1 등), `B_*`는 사진에 색 분류가 없어서 구분용으로 고른 색이다. 색 표는 `make_layers_photo2.py`의 `LAYER_COLOR`에서 바꾼다.

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
# 1) 도면 이미지 분해 (입력은 두 패널짜리 PNG, 설정 파일은 선택)
python make_layers_photo2.py my_figure.png out/my_figure my_figure.json

# 2) DXF → DWG
ODA_CONVERTER=/path/to/ODAFileConverter ./dxf_to_dwg.sh out/my_figure.dxf out/dwg

# 3) 레이어별 미리보기
python render_photo2_by_layer.py out/my_figure.gds out/my_figure_by_layer.png
```

`ODAFileConverter`가 PATH에 있으면 `ODA_CONVERTER`는 생략해도 된다.

### Windows (PowerShell)

```powershell
# 1) 패키지 설치 (Python 3.10 이상)
py -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2) 도면 이미지 분해 (Linux와 같은 명령, 설정 파일은 선택)
python make_layers_photo2.py my_figure.png out\my_figure my_figure.json

# 3) DXF → DWG (ODA 경로를 지정하고 실행)
$env:ODA_CONVERTER = "C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"
.\dxf_to_dwg.ps1 -InputDxf out\my_figure.dxf -OutputDir out\dwg

# 4) 레이어별 미리보기
python render_photo2_by_layer.py out\my_figure.gds out\my_figure_by_layer.png
```

- `dxf_to_dwg.ps1`은 Linux용 `dxf_to_dwg.sh`와 같은 ODA 인자(ACAD2018, DWG)를 쓴다. 변환 뒤 DWG 파일이 실제로 생겼는지 확인한다.
- ODA File Converter Windows 버전을 따로 설치해야 한다. 기본 경로에 없으면 `ODA_CONVERTER`로 전체 경로를 준다.
- 이 저장소의 Windows 스크립트는 Windows 실기에서 아직 실행해 보지 않았다.

## 다른 이미지에 쓸 때 주의

- **이미지마다 설정 파일을 하나씩 둔다.** `examples/photo2.json`을 복사해 `my_figure.json`을 만들고, 그 파일에서 값을 고친 뒤 세 번째 인자로 넘긴다. 설정 파일을 주지 않으면 예시 사진 값이 쓰인다.
  - `a_box`, `b_box`: 패널 a, b의 픽셀 박스 `[x0, y0, x1, y1]`. `_overlay_check.png`로 위치를 먼저 확인한다.
  - `panel_a_width_um`: 패널 a 폭(µm). 도면에 적힌 치수 표기에서 가져온다. 기본 45.
  - `manual_ring`, `manual_rect_guard`, `manual_pad`, `manual_block`: 패널 b에서 색으로 잡히지 않는 구조를 손으로 그린 좌표. 설정 파일을 주면 이 항목은 예시 값이 아니라 파일 값만 쓰고, 없는 키는 비어 있는 것으로 본다.
- 색 분류 기준(`classify_a`의 hue 구간)과 레이어 색(`LAYER_COLOR`)은 아직 설정 파일로 바꿀 수 없다. 이미지에 따라 바꿔야 하면 스크립트를 직접 고친다.
- 사진 기반이라 치수는 참고용이다.

## 예시 파일 (`examples/`)

| 파일 | 설명 |
|---|---|
| `photo2_layers.dwg` | 예시 결과 DWG (ACAD2018) |
| `photo2_layers.gds` | 예시 GDS |
| `photo2_layers_gds_map.txt` | GDS 레이어 번호와 이름 |
| `photo2_layers_preview.png` | 전체 미리보기 |
| `photo2_layers_by_layer.png` | 레이어별 미리보기 |
| `photo2.json` | 예시 사진의 설정 파일 (새 이미지 설정의 출발점) |

## 파일

- `make_layers_photo2.py` — 메인 분해 스크립트
- `dxf_to_dwg.sh` — DXF → DWG 변환 래퍼 (Linux)
- `dxf_to_dwg.ps1` — DXF → DWG 변환 래퍼 (Windows, PowerShell)
- `render_photo2_by_layer.py` — 레이어별 미리보기
- `render_photo2_preview.py` — GDS 전체 미리보기
- `requirements.txt` — 파이썬 의존성 (테스트에 쓴 버전으로 고정)
