---
layout: post
title: "Repo Deep Dive: ohmyzsh/ohmyzsh - 매일 쓰는 Zsh 환경을 구성하는 방법"
date: 2026-07-02 08:39:05 +0900
categories: [github-repo-analysis]
tags: [github, zsh, shell, terminal, developer-tools, open-source]
repo: ohmyzsh/ohmyzsh
analyzed_at: 2026-10-16
analyzed_commit: 964ddf789b022b6958b27d02d7fa54f552de21e9
---

아침에 터미널을 열고 프로젝트 디렉터리로 이동한다. 현재 브랜치를 확인하고, 수정한 파일을 비교한 다음 필요한 변경만 커밋한다. 이때 입력을 받는 창, 명령을 해석하는 프로그램, 프롬프트와 별칭을 준비하는 설정은 서로 다른 역할을 한다. Oh My Zsh를 이해하려면 이 세 가지부터 구분해야 한다.

터미널 앱은 글자를 보여 주고 키보드 입력을 전달하는 창이다. Zsh는 그 안에서 `cd` 같은 내장 명령을 처리하거나 Git 같은 외부 프로그램을 실행하는 셸이다. Oh My Zsh는 Zsh가 시작할 때 불러오는 설정 프레임워크다. 자주 쓰는 기능을 플러그인으로 선택하고, 프롬프트를 테마로 정하며, 설정을 공통된 방식으로 관리하도록 돕는다.

이 글은 기존 게시일과 별도로 2026년 10월 16일 재검토 기준의 공식 문서와 위 커밋을 바탕으로 다시 작성했다. 아래 설정과 명령은 문서 및 소스로 확인한 설명용 예시이며, 이 검토에서 셸 설치나 Git 작업을 직접 실행하지는 않았다.

## 터미널을 열었을 때 실제로 일어나는 일

Oh My Zsh를 설치했다고 모든 터미널 창이 같은 환경이 되는 것은 아니다. 해당 창에서 Zsh를 실행해야 한다. PowerShell이나 Bash를 실행 중이면 Zsh용 설정이 그 셸을 바꾸어 주지 않는다. Windows에서 공식 README가 지원 대상으로 제시하는 환경도 WSL2다. 먼저 사용할 셸과 실행 환경을 정하고, 그 위에 Oh My Zsh 설정을 올리는 순서로 접근해야 한다.

Zsh는 대화형 셸을 시작할 때 사용자 설정 파일 `.zshrc`를 읽는다. 보통 홈 디렉터리에 있지만 `ZDOTDIR`를 설정했다면 그 위치가 기준이 된다. 로그인 셸 여부에 따라 `.zprofile`, `.zlogin` 등도 읽으므로 모든 시작 설정이 `.zshrc` 한 파일에 있는 것은 아니다. 여기서 다루는 플러그인과 프롬프트는 대화형 작업에 쓰는 `.zshrc`를 중심으로 이해하면 된다. 이 구분은 [Zsh의 시작 파일 문서](https://zsh.sourceforge.io/Doc/Release/Files.html#Startup_002fShutdown-Files)에 명시되어 있다.

Oh My Zsh의 기본 설치 위치는 `~/.oh-my-zsh`다. `.zshrc`는 이 경로를 `ZSH` 변수로 가리키고, `oh-my-zsh.sh`를 현재 셸 안으로 읽어 들인다. 플러그인 이름을 적어 두는 것만으로는 충분하지 않다. 실제 초기화 파일을 `source`해야 그 셸에 별칭과 함수가 생긴다.

처음 도입할 때도 기존 설정을 살펴야 한다. 공식 설치 절차는 기존 `.zshrc`를 `.zshrc.pre-oh-my-zsh`로 옮긴다고 설명한다. 이전에 설정한 개발 도구 경로나 환경 변수는 새 파일과 비교해 필요한 내용을 옮겨야 한다. Zsh, Git, 다운로드 도구 등의 전제와 설치 스크립트를 먼저 살펴보는 방법은 [공식 설치 안내](https://github.com/ohmyzsh/ohmyzsh/blob/964ddf789b022b6958b27d02d7fa54f552de21e9/README.md#getting-started)에서 확인할 수 있다.

## `.zshrc`에서는 값보다 순서가 중요하다

Git을 주로 사용하는 사람의 설정을 간단히 구성하면 다음과 같다. 공식 기본 템플릿을 토대로 업데이트 정책과 개인 별칭을 덧붙인 예시다.

```zsh
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"
plugins=(git)

zstyle ':omz:update' mode reminder

source "$ZSH/oh-my-zsh.sh"

alias croot='cd ~/work'
```

앞부분은 Oh My Zsh를 불러올 때 참고할 선택 사항이다. 어느 경로에서 읽을지, 어떤 테마를 적용할지, 어떤 플러그인을 활성화할지를 먼저 선언한다. `source` 다음은 초기화가 끝난 셸에 추가로 적용할 개인 설정이다. 기본 별칭을 자신의 것으로 바꾸고 싶다면 이 위치에 정의할 수 있다. `croot`는 이 글에서 만든 개인 별칭이며 기본 제공 기능이 아니다. [공식 `.zshrc` 템플릿](https://github.com/ohmyzsh/ohmyzsh/blob/964ddf789b022b6958b27d02d7fa54f552de21e9/templates/zshrc.zsh-template)도 플러그인 선언, 초기화, 사용자 설정을 이 순서로 배치한다.

순서를 거꾸로 두면 왜 설정이 적용되지 않는지도 설명할 수 있다. 초기화가 끝난 뒤 `plugins=(git docker)`로 배열을 바꾸어도 이미 끝난 로딩이 자동으로 다시 일어나지는 않는다. 테마 이름과 업데이트 설정도 이를 읽는 초기화보다 앞에 있어야 한다. 플러그인 배열은 `plugins=(git docker)`처럼 공백으로 구분하고 쉼표를 넣지 않는다. 여러 개를 지정하면 배열 순서대로 읽는다. 이는 [공식 설정 문서](https://github.com/ohmyzsh/ohmyzsh/wiki/Settings#main-settings)에 정리되어 있다.

현재 소스에서 초기화 흐름은 자동완성 준비와 공통 라이브러리 로딩, 선택한 플러그인 로딩, 사용자 `custom/*.zsh` 로딩, 테마 로딩으로 이어진다. 플러그인의 자동완성 경로는 자동완성 초기화 전에 등록한다. 따라서 개인 설정이라고 모두 같은 시점에 적용되는 것은 아니다. 특히 프롬프트를 직접 덮어쓰려면 사용자 파일 뒤에 테마가 로딩된다는 점도 고려해야 한다. 이 순서는 검토한 [초기화 소스](https://github.com/ohmyzsh/ohmyzsh/blob/964ddf789b022b6958b27d02d7fa54f552de21e9/oh-my-zsh.sh)를 기준으로 보는 편이 정확하다.

파일을 고친 뒤에는 새 Zsh 세션에서 확인하는 방식이 이해하기 쉽다. 설정 파일에서 플러그인을 지웠다는 사실만으로 현재 셸에 이미 정의된 모든 별칭이 즉시 사라지는 것은 아니다. 시작 설정과 지금 실행 중인 셸의 상태를 구분해야 설정을 고쳤는데도 동작이 남아 있는 상황을 해석할 수 있다.

## Git 작업에서 플러그인의 효과가 드러난다

기본 템플릿은 `git` 플러그인을 활성화한다. 이 플러그인은 Git을 새로 구현하는 대신 자주 쓰는 명령에 짧은 이름을 붙이고 보조 함수를 제공한다. 처음부터 모든 이름을 외우기보다는 하루에 반복하는 동작 몇 개와 연결하면 된다.

| 입력 | 실행되는 명령 | 확인하거나 바꾸는 것 |
| --- | --- | --- |
| `gst` | `git status` | 현재 브랜치와 변경 상태 |
| `gd` | `git diff` | 아직 스테이지에 올리지 않은 차이 |
| `ga README.md` | `git add README.md` | 지정한 파일을 스테이지에 추가 |
| `gcmsg "docs: clarify setup"` | `git commit --message "docs: clarify setup"` | 스테이지에 올린 변경을 커밋 |
| `glog` | `git log --oneline --decorate --graph` | 간결한 커밋 그래프 |

위 대응은 [Git 플러그인 문서](https://github.com/ohmyzsh/ohmyzsh/blob/964ddf789b022b6958b27d02d7fa54f552de21e9/plugins/git/README.md)와 [별칭 정의 소스](https://github.com/ohmyzsh/ohmyzsh/blob/964ddf789b022b6958b27d02d7fa54f552de21e9/plugins/git/git.plugin.zsh)에서 확인했다. 문서를 고쳤다면 `gst`로 변경 범위를 보고 `gd`로 내용을 읽은 뒤 필요한 파일만 `ga`로 선택한다. 그다음 `gcmsg`를 실행하고 `glog`로 결과를 확인한다. 타이핑은 줄어도 상태 확인, 변경 선택, 커밋이라는 Git의 절차는 같다.

별칭은 옵션의 의미까지 지워 주지는 않는다. `gp`는 `git push`이고 `gpf!`는 강제 푸시를 수행하는 이름이다. 짧은 입력이 익숙해질수록 실제로 어떤 명령인지 알고 사용해야 한다. 새 이름이 혼란스럽다면 `alias gst`처럼 정의를 확인하거나 원래 `git status`를 그대로 사용해도 된다. 이 셸에서 편하다는 이유로 다른 컴퓨터나 자동화 스크립트에도 같은 별칭이 있다고 가정해서는 안 된다.

다른 도구도 비슷한 방식으로 확장한다. Docker 작업이 잦다면 `docker` 플러그인을 활성화해 자동완성과 별칭을 사용할 수 있다. 예를 들어 `dps`는 `docker ps`, `dlo`는 `docker container logs`에 대응한다. 이때 Oh My Zsh가 Docker 실행파일이나 엔진을 설치해 주는 것은 아니다. 해당 명령을 실행할 수 있는 환경은 별도로 준비해야 한다. 플러그인이 제공하는 범위가 자동완성과 별칭이라는 점은 [Docker 플러그인 문서](https://github.com/ohmyzsh/ohmyzsh/blob/964ddf789b022b6958b27d02d7fa54f552de21e9/plugins/docker/README.md)에서도 확인할 수 있다.

플러그인 목록은 필요한 프로그램을 내려받는 패키지 목록이 아니다. 기본 제공 플러그인을 선택하면 설치 디렉터리에 들어 있는 관련 설정을 읽는다. 외부 플러그인이라면 그 플러그인의 파일을 준비하는 과정과 활성화하는 과정도 구분해야 한다. 쓰지 않는 항목을 모두 켜기보다는 실제로 사용할 기능을 문서에서 확인해 추가하는 편이 낫다. 기본 템플릿도 플러그인을 많이 켜면 셸 시작이 느려질 수 있다고 안내한다.

## 테마는 작업 위치를 읽는 프롬프트다

매번 `pwd`와 `git branch`를 실행하지 않아도 현재 위치와 브랜치를 프롬프트에서 읽을 수 있다면 작업 맥락을 확인하기가 편해진다. 기본 `robbyrussell` 테마는 현재 디렉터리 표시와 `git_prompt_info`를 조합하고 Git 상태에 따라 표시를 붙인다. 명령을 입력하는 자리에서 필요한 정보를 보여 주는 구성이다. 실제 조합은 짧은 [테마 소스](https://github.com/ohmyzsh/ohmyzsh/blob/964ddf789b022b6958b27d02d7fa54f552de21e9/themes/robbyrussell.zsh-theme)에서 볼 수 있다.

테마를 바꾸려면 `.zshrc`의 `ZSH_THEME`를 원하는 이름으로 바꾼다. 다만 스크린샷과 다른 모양이 나온다고 플러그인 로딩부터 의심할 필요는 없다. 테마는 프롬프트를 정하며, 창의 색상표와 글꼴 선택은 터미널 앱이 담당한다. 일부 테마는 Powerline Font나 Nerd Font의 기호를 전제로 하므로 해당 글꼴을 설치하고 터미널에서 선택해야 문자가 제대로 보인다. 모든 테마에 특수 글꼴이 필요한 것은 아니다. 이런 범위와 글꼴 전제는 [공식 테마 선택 안내](https://github.com/ohmyzsh/ohmyzsh/blob/964ddf789b022b6958b27d02d7fa54f552de21e9/README.md#selecting-a-theme)에 설명되어 있다.

프롬프트에 브랜치가 표시되어도 실제 변경 내용을 검토한 것은 아니다. 화면의 상태 표시는 작업 맥락을 빠르게 읽는 데 쓰고, 커밋 전 확인은 `gst`와 `gd` 같은 명령으로 수행하는 역할 분담이 자연스럽다.

## 오래 쓰려면 개인 설정의 위치를 정한다

몇 주가 지나면 개인 별칭과 함수가 늘어난다. 이때 기본 플러그인이나 테마 파일을 직접 고치면 원본 업데이트와 자신의 수정이 뒤섞인다. Oh My Zsh는 이를 위해 `$ZSH_CUSTOM`을 제공한다. 기본값은 `$ZSH/custom`이며 그 아래의 `aliases.zsh` 같은 최상위 `.zsh` 파일에 개인 설정을 둘 수 있다.

여러 함수를 하나의 플러그인으로 관리한다면 `$ZSH_CUSTOM/plugins/mytools/mytools.plugin.zsh`처럼 파일을 만들고 `plugins` 배열에 `mytools`를 추가한다. 사용자 테마는 `$ZSH_CUSTOM/themes`에 둔다. 기본 제공 플러그인과 같은 이름의 사용자 플러그인은 원본 대신 로딩되므로 간단한 별칭 하나를 추가하려고 전체 플러그인을 복제할 필요는 없다. 위치를 별도의 설정 저장소로 옮기고 싶다면 `.zshrc`에서 `ZSH_CUSTOM`을 초기화 전에 지정할 수도 있다. 구체적인 규칙은 [공식 사용자 설정 안내](https://github.com/ohmyzsh/ohmyzsh/wiki/Customization)에 정리되어 있다.

업데이트도 이 환경의 일부다. 기본 모드는 업데이트 전에 확인을 요청하며 위 예시는 알림을 받은 뒤 사용자가 시점을 고르는 `reminder` 모드를 선택했다. 자동 적용은 `auto`, 자동 확인을 끄는 모드는 `disabled`다. 수동 업데이트 명령은 `omz update`이며 이는 Oh My Zsh를 갱신하는 명령이다. Git이나 Docker 등 외부 도구의 업데이트까지 맡지는 않는다. 모드와 확인 주기를 조정하는 방법은 [업데이트 설정 문서](https://github.com/ohmyzsh/ohmyzsh/wiki/Settings#update-settings)에서 확인할 수 있다.

이 저장소는 반복해서 만드는 셸 설정을 공통 틀로 묶고 필요한 부분을 선택할 수 있게 한다. Git을 하루에도 여러 번 쓰거나 여러 개발 도구의 명령을 오가는 Zsh 사용자라면 효용을 바로 이해할 수 있다. 반대로 짧은 별칭과 추가 테마가 필요 없다면 기본 Zsh 설정만으로도 충분할 수 있다. 선택의 기준은 기능 개수보다 자신이 입력하는 명령과 관리해야 할 설정이다. 저장소의 [MIT 라이선스](https://github.com/ohmyzsh/ohmyzsh/blob/964ddf789b022b6958b27d02d7fa54f552de21e9/LICENSE.txt)도 함께 확인할 수 있다.

## 참고 자료

- [Oh My Zsh 공식 저장소와 README](https://github.com/ohmyzsh/ohmyzsh/tree/964ddf789b022b6958b27d02d7fa54f552de21e9)
- [기본 `.zshrc` 템플릿](https://github.com/ohmyzsh/ohmyzsh/blob/964ddf789b022b6958b27d02d7fa54f552de21e9/templates/zshrc.zsh-template)
- [Git 플러그인 사용 문서](https://github.com/ohmyzsh/ohmyzsh/blob/964ddf789b022b6958b27d02d7fa54f552de21e9/plugins/git/README.md)
- [공식 설정 위키](https://github.com/ohmyzsh/ohmyzsh/wiki/Settings)
- [사용자 플러그인과 테마 관리](https://github.com/ohmyzsh/ohmyzsh/wiki/Customization)
