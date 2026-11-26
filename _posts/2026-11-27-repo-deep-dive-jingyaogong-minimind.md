---
layout: post
title: "Repo Deep Dive: jingyaogong/minimind — 작은 언어 모델을 처음부터 학습하고 추론까지 연결하기"
date: 2026-11-27 07:11:08 +0900
categories: [github-repo-analysis]
repo: jingyaogong/minimind
trending_rank: 4
trending_period: daily
trending_checked_at: 2026-11-27 07:10:29 +0900
trending_url: https://github.com/trending?since=daily
---

2026년 11월 27일 07:10 KST에 확인한 GitHub Trending 일간 전체 언어 목록에서 `jingyaogong/minimind`는 4위였다. **이는 저장소를 선정한 시점의 스냅샷이지, 발행 시점이나 현재의 실시간 순위가 아니다.** 아래 내용은 프로젝트의 현재 README, 영문 사용 안내, 학습·추론 스크립트와 공개 데이터 안내를 대조했다. 실제 GPU 학습이나 모델 품질 평가는 이 글에서 수행하지 않았다.

## 1. 프로젝트 소개

MiniMind는 Jingyao Gong이 공개·유지하는 초소형 언어 모델 학습 프로젝트다. 이미 학습된 거대 모델을 API로 호출하는 서비스가 아니라, 모델 구조를 살펴보고 데이터로 사전학습한 다음 대화용 지도 미세조정(SFT)을 거쳐 직접 추론해 볼 수 있는 코드와 학습 자료를 함께 제공한다. 현재 주력 모델 `minimind-3`는 약 64M 매개변수의 Dense 모델이며, 전문가 혼합(MoE) 버전도 별도로 공개한다. 공식 README는 PyTorch로 핵심 학습 과정을 직접 구현해 모델 내부를 공부할 수 있도록 하는 교육 목적을 분명히 밝힌다. 이미 만들어진 Transformers 형식 가중치를 내려받아 곧바로 대화해 보는 경로와, 데이터부터 내려받아 자신의 가중치를 만드는 경로가 나뉜다.

README 제목의 ‘2시간·3위안’은 모델 개발 전체를 처음부터 끝까지 그 시간과 비용으로 마칠 수 있다는 보장이 아니다. 프로젝트 설명에 따르면 단일 NVIDIA 3090에서 **SFT 1 epoch**를 수행한 측정치와 그 구간의 GPU 임대 비용을 가리킨다. 사전학습, 데이터 다운로드·준비, 장비 확보와 이후 단계의 시간은 별개다. 개인 GPU나 제한된 실험 환경에서 전체 과정을 이해하려는 개발자에게 맞는 프로젝트이지, 작은 크기만으로 상용 대형 모델과 동등한 정확도를 약속하는 제품은 아니다.

## 2. 해결하려는 문제

일반적인 대형 언어 모델을 처음부터 학습하기에는 데이터와 연산 자원이 지나치게 크다. 반면 기존 모델에 LoRA만 덧붙여 미세조정하면 실제 토크나이저, 모델의 다음 토큰 예측, 학습 손실, 체크포인트가 어떻게 연결되는지 살피기 어렵다. 고수준 라이브러리의 편의 함수만 사용하는 경우에도 몇 줄의 호출 뒤에서 어떤 상태가 저장되고 어느 가중치가 다음 단계의 출발점이 되는지 놓치기 쉽다. MiniMind는 규모를 줄이고 사전학습·SFT·추론을 독립적으로 실행할 수 있게 해 이 연결을 확인하도록 한다.

핵심은 ‘학습을 시작한다’와 ‘대화 모델을 얻는다’가 서로 다른 단계라는 점이다. 사전학습은 텍스트의 다음 토큰을 예측하도록 기본 언어 패턴을 익히고 `pretrain_*.pth` 가중치를 만든다. SFT는 그 가중치를 시작점으로 사용자·어시스턴트 역할이 있는 대화 자료를 학습해 `full_sft_*.pth`를 만든다. 저장소의 기본 학습 인수를 보면 SFT 스크립트의 `--from_weight`는 `pretrain`이고, 추론 스크립트의 기본 `--weight`는 `full_sft`다. 따라서 사전학습 출력 없이 기본 SFT 명령만 실행하거나, 학습된 가중치 없이 PyTorch 추론 경로를 실행해서 완성된 모델을 얻는 구조가 아니다.

## 3. 주요 기능

**모델을 학습하는 두 필수 단계.** 현재 기본 사전학습 입력은 `pretrain_t2t_mini.jsonl`, 기본 SFT 입력은 `sft_t2t_mini.jsonl`이다. 두 스크립트 모두 `--data_path`로 다른 자료를 지정할 수 있으며, 기본 768 차원의 모델 설정을 사용한다. 사전학습 결과의 이름은 `pretrain_768.pth` 같은 형태이고, SFT 결과는 `full_sft_768.pth` 형태다. 학습 중에는 손실·학습률 로그가 나와 진행 상태를 볼 수 있고, 재시작을 위한 별도 체크포인트도 기록된다. 추론에 쓰는 가중치 파일과 학습 상태를 복구하는 체크포인트를 같은 산출물로 혼동하지 않아야 한다.

**직접 대화와 배포용 추론 경로.** `eval_llm.py`는 Transformers 형식 모델 폴더 또는 프로젝트의 PyTorch 가중치를 읽는다. 사용자는 입력 방식, 생성 길이, 온도, 대화 이력 수, `--open_thinking` 등을 지정하고 프롬프트를 입력해 생성 응답을 확인한다. 코드상 PyTorch 경로는 선택한 `--weight` 접두사와 `--hidden_size`를 조합해 가중치를 찾는다. 반면 Transformers 경로는 지정한 모델 폴더에서 모델을 읽는다. Streamlit WebUI와 `/v1/chat/completions`를 제공하는 FastAPI 예제도 있다. API 스크립트는 응답에서 일반 텍스트와 `reasoning_content`, `tool_calls`를 구분하도록 작성되어 있지만, 실제 클라이언트 호환성은 사용할 모델과 요청 형식으로 확인해야 한다.

**선택적 학습·실험 단계.** 기본 대화 모델을 만드는 두 단계 뒤에 LoRA, DPO, GRPO, PPO, 증류, Agentic RL 같은 실험을 더할 수 있다. 예를 들어 LoRA는 기본 모델의 모든 매개변수를 다시 조정하는 대신 낮은 차원의 추가 가중치를 학습하고, 추론 시 기본 가중치와 LoRA 가중치를 함께 지정한다. 도구 호출 예제는 `system`의 도구 정의, 어시스턴트의 `tool_calls`, 도구 응답을 잇는 대화 형식을 사용하며 `eval_toolcall.py`로 테스트한다. README도 이 도구 호출 능력의 일반화가 제한적이라고 명시한다. `open_thinking`은 별도의 ‘추론 전용’ 가중치를 고르는 옵션이 아니라 현재 채팅 템플릿에서 생각 태그를 어떻게 열지 조정하는 스위치다.

## 4. 사용 방법과 동작 흐름

빠르게 동작을 살피려면 학습보다 공개 가중치 추론부터 시작할 수 있다. README의 참고 환경은 Python 3.10.16, CUDA 12.2, NVIDIA 3090이지만 이것이 모든 사용자의 필수 조합이라는 뜻은 아니다. 먼저 자신이 사용할 PyTorch가 GPU를 인식하는지 확인하고, 저장소 의존성을 설치한다. 공개된 Transformers 형식 모델을 받아 아래처럼 실행하면 훈련 출력 파일을 직접 만들지 않아도 CLI 대화를 시도할 수 있다.

```bash
git clone --depth 1 https://github.com/jingyaogong/minimind
cd minimind
pip install -r requirements.txt
modelscope download --model gongjy/minimind-3 --local_dir ./minimind-3
python eval_llm.py --load_from ./minimind-3
```

마지막 명령은 자동 테스트 또는 직접 입력 모드를 고르는 프롬프트를 표시한다. 자동 테스트의 예시 응답은 생성 결과이지 정확도 검증 결과가 아니다. 직접 입력 모드에서 질문을 주면 생성된 텍스트를 보고 모델이 어떻게 응답하는지 확인할 수 있다. CPU에서도 실행 경로는 있지만, 속도와 메모리 요구는 실행 환경에 따라 달라진다.

처음부터 학습하려면 공식 데이터 저장소에서 `pretrain_t2t_mini.jsonl`과 `sft_t2t_mini.jsonl`을 내려받아 프로젝트의 `dataset` 위치에 둔다. 해당 두 파일은 README가 빠른 재현용으로 추천한 조합이다. 그 후 다음 순서로 학습한다.

```bash
cd trainer
python train_pretrain.py
python train_full_sft.py
cd ..
python eval_llm.py --weight full_sft
```

첫 학습 스크립트는 기본적으로 `pretrain` 가중치를 저장하고, 둘째 스크립트는 이를 이어받아 `full_sft` 가중치를 저장한다. 마지막 명령은 그 SFT 가중치를 로드한다. 결과를 읽을 때는 학습 로그의 손실 감소, 저장된 가중치 파일, 실제 질문에 대한 출력이라는 세 가지를 구분해야 한다. 손실만 낮아졌다고 사실성이나 도구 사용이 검증된 것은 아니다. 중단된 학습은 각 스크립트에 `--from_resume 1`을 주어 체크포인트에서 재개할 수 있다. 여러 GPU를 쓸 때는 문서처럼 `trainer` 위치에서 `torchrun --nproc_per_node N`으로 해당 학습 스크립트를 실행한다. 이 글에서는 소요 시간이나 성능을 재현해 측정하지 않았다.

## 5. 활용 사례

**학습 단계별 출력을 비교하는 실습.** 공식 README는 사전학습 뒤 `python eval_llm.py --weight pretrain`, SFT 뒤 `--weight full_sft`로 각각 질문해 보는 예를 제시한다. 같은 질문에 대한 출력을 비교하면 텍스트 이어쓰기 단계와 대화 형식 학습 단계가 실제로 어떤 차이를 만드는지 관찰할 수 있다. 이는 프로젝트가 공개한 예시 절차이며, 몇 개 질문의 응답만으로 모델의 일반적 성능을 평가한다는 뜻은 아니다.

**도구 사용 흐름 검토.** 문서의 계산 예제는 사용자의 곱셈 요청을 도구 호출로 바꾸고, `calculate_math` 결과를 받은 뒤 최종 답을 쓰는 대화 순서를 보여 준다. `python eval_toolcall.py --weight full_sft`는 현재 SFT 가중치의 도구 호출을 시험하는 공식 예시다. 여기서 확인할 것은 최종 문장뿐 아니라 생성된 도구 이름·인수, 도구 응답을 받은 후의 답변이다. 공개 자료는 소수의 모의 도구와 합성 학습 예시에 기반하므로 임의 외부 API를 안정적으로 호출한다고 확대 해석하면 안 된다.

**로컬 대화 인터페이스 연결.** README는 Streamlit 화면과 OpenAI 호환 API 서버를 별도로 안내한다. 화면을 쓰려면 Transformers 형식 모델 폴더를 `scripts` 아래에 복사한 뒤 `cd scripts && streamlit run web_demo.py`를 실행한다. 서버 예제는 `serve_openai_api.py`의 `/v1/chat/completions`를 통해 메시지와 선택적인 도구·생각 모드를 받아 응답을 만든다. 둘 다 훈련 자체를 대신하는 기능은 아니며, 앞서 준비한 모델 가중치를 사람이 대화하거나 클라이언트가 요청할 수 있는 형태로 노출하는 사용 사례다.

## 6. 참고 자료

- [MiniMind 저장소 및 현재 README](https://github.com/jingyaogong/minimind) — 프로젝트 목적, 단계별 빠른 시작, 실험·제약 설명
- [영문 사용 안내](https://github.com/jingyaogong/minimind/blob/master/README_en.md) — 추론, 학습, 도구 호출 예시
- [공개 학습 데이터](https://www.modelscope.cn/datasets/gongjy/minimind_dataset/files) — 빠른 재현용 JSONL 파일
- [공개 `minimind-3` 모델](https://www.modelscope.cn/models/gongjy/minimind-3) — Transformers 형식 모델 다운로드 경로
- [사전학습·SFT 스크립트](https://github.com/jingyaogong/minimind/tree/master/trainer) — 기본 입력, 가중치 저장, 재개 옵션
- [CLI 추론 코드](https://github.com/jingyaogong/minimind/blob/master/eval_llm.py) 및 [OpenAI 호환 API 예제](https://github.com/jingyaogong/minimind/blob/master/scripts/serve_openai_api.py) — 모델 로드와 응답 처리 방식
