# cad-reverse

두 패널짜리 도면 이미지를 색(hue)으로 나눠 **레이어별 도형**으로 분해하고, 그 결과를 GDS와 DXF를 거쳐 **DWG**로 저장하는 스크립트 모음.

> 근사치다. 사진에는 레이어 정보가 없어서 색과 위치로 추정한 결과이고, 파운드리 설계 규칙이나 DRC 검사를 거치지 않았다. 축척은 패널 폭 45 µm 표기를 기준으로 가정했다.

## 파이프라인

```
도면 이미지(PNG) + 이미지별 설정 파일(JSON)
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

## 실행 방법 (Linux / macOS)

아래 순서를 그대로 따라 하면 된다. 예시 입력 PNG는 저장소에 없고 예시 **결과물**만 `examples/`에 있다. 그래서 1단계에서 본인 이미지를 준비한다.

### 1) 입력 이미지 준비

- 두 패널이 좌우로 나란히 있는 PNG 한 장.
- 왼쪽 패널을 **패널 a**(픽셀 배치, 색으로 레이어 구분), 오른쪽 패널을 **패널 b**(센서 구조)로 본다.
- 두 패널의 위치는 설정 파일에서 픽셀 좌표로 지정한다. 이미지 크기는 자유지만, 패널이 잘리지 않아야 한다.

### 2) 출력 폴더 만들기

스크립트는 출력 폴더를 자동으로 만들지 않는다. 없으면 파일 쓰기에서 실패한다.

```bash
mkdir -p out/dwg
```

### 3) 이미지별 설정 파일 만들기

이미지마다 설정 파일을 하나씩 둔다. 예시 설정을 복사해서 고친다.

```bash
cp examples/photo2.json my_figure.json
```

`my_figure.json`의 항목:

| 키 | 뜻 | 형식 |
|---|---|---|
| `a_box` | 패널 a 영역(사진 픽셀). 패널 a의 검은 테두리까지 포함한다 | `[x0, y0, x1, y1]` |
| `b_box` | 패널 b 영역(사진 픽셀) | `[x0, y0, x1, y1]` |
| `panel_a_width_um` | 패널 a의 실제 폭(µm). 도면에 적힌 치수 표기를 쓴다 | 숫자 (예: `45.0`) |
| `manual_ring` | 패널 b의 가드링 프레임을 손으로 그린 좌표. 바깥 사각형과 안쪽 사각형을 한 쌍으로 쓴다 | `[[[외곽 x0,y0,x1,y1], [내곽 x0,y0,x1,y1]], ...]` |
| `manual_rect_guard` | 패널 b의 가드링 띠(사각형) 좌표 | `[[x0,y0,x1,y1], ...]` |
| `manual_pad` | 패널 b의 작은 정사각형(패드) 좌표 | `[[x0,y0,x1,y1], ...]` |
| `manual_block` | 패널 b의 블록 안쪽 정사각형 좌표 | `[[x0,y0,x1,y1], ...]` |

- 좌표는 모두 **사진 전체 기준 픽셀**이다. 패널 안에서의 상대 좌표가 아니다.
- `manual_*`는 색으로 잡히지 않는 구조를 손으로 넣는 것이다. 설정 파일을 주면 예시 사진의 수작업 좌표는 쓰이지 않는다. 필요한 항목만 넣고, 없는 키는 빈 목록으로 본다.
- `a_box`나 `b_box`를 빼면 예시 사진 값이 채워진다. 새 이미지에서는 두 박스를 반드시 직접 넣는다.
- `panel_a_width_um`은 `a_box`의 가로 길이가 실제로 몇 µm인지 정한다. 축척(µm/px)은 이 값과 `a_box` 폭으로 계산된다. 패널 b도 같은 축척을 쓴다고 가정한다.
- JSON 문법을 틀리면(쉼표, 따옴표) 바로 실패한다. `python -m json.tool my_figure.json`으로 먼저 검사할 수 있다.

### 4) 분해 실행

```bash
python make_layers_photo2.py my_figure.png out/my_figure my_figure.json
```

- 인자는 순서대로 **입력 PNG**, **출력 접두사**, **설정 JSON**이다. 세 번째 인자는 생략할 수 있지만, 새 이미지라면 생략하지 않는다.
- 출력 접두사 `out/my_figure`에 아래 파일이 생긴다.
  - `out/my_figure.gds`
  - `out/my_figure.dxf`
  - `out/my_figure_gds_map.txt`: 레이어별 도형 수. 여기서 0인 레이어가 많으면 색 기준이 맞지 않는 것이다(아래 문제 해결 참고).
  - `out/my_figure_overlay_check.png`: 추출 결과를 원본 위에 겹쳐 본 그림
  - `out/my_figure_geom.pkl`: 중간 좌표

### 5) 박스 위치 확인과 반복

`out/my_figure_overlay_check.png`를 열어 확인한다.

- 노란 점선 박스: `a_box`, `b_box`. 각 패널 전체를 감싸야 한다.
- 하늘색 박스: 패널 b의 토프메탈(TOPMETAL) 영역
- 연두색 박스: 패널 b의 가드링(GUARD_RING) 영역
- 자홍색 원: 다이오드(DIODE)

박스가 패널에서 벗어나 있으면 `my_figure.json`의 좌표를 고치고 4단계를 다시 돌린다. 사진 픽셀 좌표는 이미지 편집기에서 커서 위치로 읽으면 된다.

### 6) DXF를 DWG로 변환

```bash
ODA_CONVERTER=/path/to/ODAFileConverter ./dxf_to_dwg.sh out/my_figure.dxf out/dwg
```

- 결과는 `out/dwg/my_figure.dwg`다. DXF와 같은 이름에 확장자만 `.dwg`로 바뀐다.
- `ODAFileConverter`가 PATH에 있으면 `ODA_CONVERTER=...`는 생략해도 된다.
- 변환 형식은 ACAD2018 DWG다.

### 7) 레이어별 미리보기

```bash
python render_photo2_by_layer.py out/my_figure.gds out/my_figure_by_layer.png
```

레이어마다 한 칸씩, 해당 레이어 도형을 색으로 칠하고 나머지는 흐린 회색으로 보여 준다.

### 참고: GDS 전체 미리보기

`render_photo2_preview.py`는 GDS 한 장을 두 패널로 보여 준다. 인자는 `GDS 경로`와 `출력 PNG 경로`다.

```bash
python render_photo2_preview.py out/my_figure.gds out/my_figure_preview.png
```

## 실행 방법 (Windows, PowerShell)

Linux와 같은 단계다. 차이는 경로 구분자(`\`)와 DWG 변환 스크립트뿐이다.

```powershell
# 0) 1회 설정: 이 PowerShell 창에서만 스크립트 실행 허용
Set-ExecutionPolicy -Scope Process Bypass

# 1) 패키지 설치 (Python 3.10 이상)
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2) 출력 폴더 만들기
New-Item -ItemType Directory -Force out\dwg | Out-Null

# 3) 설정 파일 만들기 (examples\photo2.json을 복사해서 고친다)
Copy-Item examples\photo2.json my_figure.json

# 4) 도면 이미지 분해 (박스 위치는 out\my_figure_overlay_check.png로 확인)
python make_layers_photo2.py my_figure.png out\my_figure my_figure.json

# 5) DXF → DWG (ODA 경로를 지정하고 실행)
$env:ODA_CONVERTER = "C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"
.\dxf_to_dwg.ps1 -InputDxf out\my_figure.dxf -OutputDir out\dwg

# 6) 레이어별 미리보기
python render_photo2_by_layer.py out\my_figure.gds out\my_figure_by_layer.png
```

- `dxf_to_dwg.ps1`은 Linux용 `dxf_to_dwg.sh`와 같은 ODA 인자(ACAD2018, DWG)를 쓴다. 변환 뒤 DWG 파일이 실제로 생겼는지 확인하고, 없으면 오류를 낸다.
- ODA File Converter Windows 버전을 따로 설치해야 한다. 기본 경로에 없으면 `$env:ODA_CONVERTER`로 전체 경로를 준다. 경로에 공백이 있으니 큰따옴표로 감싼다.
- 이 저장소의 Windows 스크립트는 Windows 실기에서 아직 실행해 보지 않았다. 문제가 생기면 오류 메시지 전체를 알려 주면 된다.

## 자주 생기는 문제

| 증상 | 원인과 해결 |
|---|---|
| `FileNotFoundError: out/...` | `out` 폴더가 없다. `mkdir -p out/dwg`(Windows는 `New-Item`)로 먼저 만든다 |
| `json.decoder.JSONDecodeError` | 설정 JSON 문법 오류. 쉼표와 따옴표를 확인한다 |
| `_gds_map.txt`에서 A 레이어 도형 수가 대부분 0 | 패널 a 색 분류가 이미지와 맞지 않다. `make_layers_photo2.py`의 `classify_a` 색 구간을 고쳐야 한다. 설정 파일로는 바꿀 수 없다 |
| 패널 b 구조가 엉뚱한 곳에서 잡힘 | `b_box`가 맞지 않다. `overlay_check.png`에서 박스를 다시 맞춘다 |
| 가드링, 패드, 블록이 빠짐 | 색으로 안 잡히는 구조는 `manual_*`에 손으로 넣어야 한다. 설정 파일을 주면 예시 값은 쓰이지 않는다 |
| ODA 변환이 Qt 관련 오류로 실패 | Linux에서는 시스템 Qt6를 `LD_LIBRARY_PATH`와 `QT_PLUGIN_PATH`로 지정한다(설치 섹션 참고) |
| `dxf_to_dwg.ps1`이 실행되지 않음 | 실행 정책 문제다. `Set-ExecutionPolicy -Scope Process Bypass`를 같은 창에서 먼저 실행한다 |
| DWG가 생기지 않았다는 오류 | ODA 경로(`ODA_CONVERTER`)가 틀렸거나 ODA가 실패했다. DXF 경로와 ODA 실행 파일 경로를 확인한다 |

## 다른 이미지에 쓸 때 주의

- 설정 파일은 이미지마다 따로 둔다. 예시 사진의 값이 새 이미지에 그대로 맞지는 않는다.
- 색 분류 기준(`classify_a`의 hue 구간)과 레이어 색(`LAYER_COLOR`)은 아직 설정 파일로 바꿀 수 없다. 이미지에 따라 바꿔야 하면 스크립트를 직접 고친다.
- 사진 기반이라 치수는 참고용이다.

## 예시 파일 (`examples/`)

| 파일 | 설명 |
|---|---|
| `photo2.json` | 예시 사진의 설정 파일 (새 이미지 설정의 출발점) |
| `photo2_layers.dwg` | 예시 결과 DWG (ACAD2018) |
| `photo2_layers.gds` | 예시 GDS |
| `photo2_layers_gds_map.txt` | GDS 레이어 번호와 이름 |
| `photo2_layers_preview.png` | 전체 미리보기 |
| `photo2_layers_by_layer.png` | 레이어별 미리보기 |

## 파일

- `make_layers_photo2.py` — 메인 분해 스크립트 (선택 인자로 설정 JSON)
- `examples/photo2.json` — 설정 파일 예시
- `dxf_to_dwg.sh` — DXF → DWG 변환 래퍼 (Linux)
- `dxf_to_dwg.ps1` — DXF → DWG 변환 래퍼 (Windows, PowerShell)
- `render_photo2_by_layer.py` — 레이어별 미리보기
- `render_photo2_preview.py` — GDS 전체 미리보기
- `requirements.txt` — 파이썬 의존성 (테스트에 쓴 버전으로 고정)
