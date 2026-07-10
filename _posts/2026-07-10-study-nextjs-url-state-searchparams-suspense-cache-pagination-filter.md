---
layout: post
title: "Next.js URL State 실전: searchParams, useSearchParams, Suspense, Cache Key로 검색·필터·페이지네이션을 설계하는 법"
date: 2026-07-10 11:50:00 +0900
categories: [nextjs]
tags: [study, nextjs, url-state, searchparams, use-search-params, pagination, filter, sorting, suspense, cache, app-router, performance]
permalink: /nextjs/2026/07/10/study-nextjs-url-state-searchparams-suspense-cache-pagination-filter.html
---

## 배경: 검색 조건은 작은 UI 상태처럼 보이지만, 운영에서는 라우팅·캐시·공유 가능성의 계약이 된다

Next.js App Router로 관리자 화면이나 SaaS 대시보드를 만들다 보면 거의 모든 목록 화면에 비슷한 요구사항이 붙는다.

- 이름, 이메일, 주문번호 같은 키워드 검색
- 상태, 권한, 기간, 담당자, 태그 필터
- 최신순, 마감일순, 금액순 정렬
- page, pageSize 기반 페이지네이션
- 탭 또는 세그먼트로 구분되는 목록 상태
- 새로고침해도 유지되는 조건
- 링크로 공유할 수 있는 검색 결과
- 뒤로 가기와 앞으로 가기가 자연스러운 탐색
- 검색 조건 변경 후 서버 데이터 재조회
- 필터 UI는 즉시 반응하되 결과 영역은 안정적으로 로딩

초기 구현에서는 이 상태를 React state로 처리하기 쉽다.

```tsx
"use client";

import { useState } from "react";

export function UserList() {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("active");
  const [page, setPage] = useState(1);

  // 생략: query, status, page로 API 호출
}
```

작은 내부 도구라면 이 방식도 어느 정도 동작한다. 하지만 화면이 업무 흐름의 중심이 되면 금방 한계가 드러난다.

- 새로고침하면 조건이 사라진다.
- 동료에게 링크를 보내도 같은 목록이 열리지 않는다.
- 브라우저 뒤로 가기가 검색 이전 상태로 돌아가지 않는다.
- 서버 컴포넌트에서 같은 조건으로 데이터를 가져오기 어렵다.
- 캐시 key가 UI state와 분리되어 오래된 결과가 보인다.
- 페이지네이션 중 필터를 바꿨는데 page가 유지되어 빈 결과가 나온다.
- 검색 input을 한 글자 입력할 때마다 서버 렌더링이 과도하게 발생한다.
- `useSearchParams()`를 아무 컴포넌트에서나 읽다가 정적 렌더링과 hydration 경계가 흔들린다.
- query string에 내부 ID, 권한 값, 임시 UI 상태가 뒤섞여 URL이 지저분해진다.

이 문제의 핵심은 "검색창을 어떻게 만든다"가 아니다.

> **검색·필터·정렬·페이지네이션 상태는 사용자가 보고 있는 데이터셋의 주소다. 따라서 URL state는 UI 편의 기능이 아니라 라우팅, 서버 데이터 조회, 캐시, 공유, 관측성까지 묶는 계약으로 설계해야 한다.**

이 글은 `useSearchParams()` 사용법을 얕게 소개하는 글이 아니다. 중급 이상 Next.js 개발자를 기준으로, App Router에서 URL state를 운영 가능한 수준으로 설계할 때 필요한 기준을 정리한다.

1. 어떤 상태를 URL에 올리고, 어떤 상태를 컴포넌트 내부에 남겨야 하는가
2. `page.tsx`의 `searchParams`와 Client Component의 `useSearchParams()`를 어떻게 나눠야 하는가
3. 검색·필터·정렬·페이지네이션 query schema를 어떻게 정규화해야 하는가
4. URL 변경과 서버 데이터 fetch, Suspense boundary, cache key를 어떻게 연결해야 하는가
5. `router.push`, `router.replace`, `<Link>`, native History API를 어떤 기준으로 선택해야 하는가
6. 흔한 race condition, stale layout, hydration, 빈 결과, cache leakage를 어떻게 피해야 하는가
7. 실무 코드 리뷰에서 볼 체크리스트는 무엇인가

결론부터 말하면 이렇다.

**Next.js의 URL state 설계는 query string을 읽고 쓰는 문제가 아니라, "현재 화면이 어떤 데이터셋을 대표하는지"를 서버와 클라이언트가 같은 규칙으로 해석하게 만드는 일이다.**

---

## 핵심개념 1: URL에 올릴 상태와 올리지 않을 상태를 먼저 구분한다

URL state 설계의 첫 단계는 `searchParams`를 다루는 코드가 아니다. 먼저 상태를 분류해야 한다.

URL에 올리기 좋은 상태는 보통 아래 조건을 만족한다.

- 새로고침 후에도 유지되어야 한다.
- 링크로 공유했을 때 같은 화면이 재현되어야 한다.
- 서버 데이터 조회 조건에 직접 영향을 준다.
- 브라우저 뒤로 가기와 앞으로 가기의 단위가 되어야 한다.
- 검색 엔진, 로그, 분석 도구에서 화면 의미를 파악하는 데 도움이 된다.

예시는 다음과 같다.

- `q=kim`
- `status=active`
- `role=admin`
- `sort=createdAt.desc`
- `page=3`
- `from=2026-07-01`
- `to=2026-07-31`
- `tab=pending`

반대로 URL에 올리면 비용이 더 큰 상태도 있다.

- 드롭다운이 열려 있는지 여부
- hover된 행 ID
- 모달 안에서 아직 저장하지 않은 임시 입력값
- 체크박스 다중 선택의 대량 ID 목록
- 보안상 숨겨야 하는 내부 권한 판단 값
- 서버에서 재계산 가능한 사용자 role
- 너무 빠르게 변하는 slider의 중간값
- 접근 토큰, 세션 ID, one-time secret

이 구분을 하지 않으면 query string이 금방 쓰레기장이 된다.

```text
/users?q=kim&status=active&page=2&dropdownOpen=true&hover=42&token=...
```

URL은 오래 남는다. 브라우저 history, 서버 로그, 분석 도구, 오류 리포트, 공유 링크에 남을 수 있다. 따라서 URL에 올리는 값은 "공개 가능한 화면 조건"이어야 한다.

실무 기준은 아래처럼 잡으면 좋다.

| 상태 종류 | URL 적합도 | 이유 |
| --- | --- | --- |
| 검색어 | 높음 | 결과셋을 정의하고 공유 가치가 있음 |
| 필터 | 높음 | 서버 조회 조건과 직접 연결됨 |
| 정렬 | 높음 | 결과 순서를 정의함 |
| 페이지 번호 | 높음 | 현재 결과 위치를 나타냄 |
| 탭 | 보통~높음 | 데이터셋이 바뀌면 URL에 두는 편이 좋음 |
| 열린 패널 | 낮음~보통 | 화면 의미보다 UI 편의 상태인 경우가 많음 |
| 입력 중 임시값 | 낮음 | debounce 전까지는 URL을 오염시킬 수 있음 |
| 선택된 행 목록 | 낮음 | 너무 길어지고 공유 의미가 약할 수 있음 |
| 인증·권한 값 | 금지 | 보안 입력으로 취급하면 안 됨 |

중요한 원칙은 단순하다.

> **URL은 화면의 재현 가능한 의미를 담고, 컴포넌트 state는 순간적인 상호작용을 담는다.**

검색 input의 "입력 중인 값"과 "서버 결과에 적용된 검색어"를 분리하는 이유도 여기에 있다.

```tsx
"use client";

import { useState, useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

export function SearchBox() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const [draft, setDraft] = useState(searchParams.get("q") ?? "");

  function applySearch() {
    const next = new URLSearchParams(searchParams);

    if (draft.trim()) {
      next.set("q", draft.trim());
    } else {
      next.delete("q");
    }

    next.delete("page");

    startTransition(() => {
      router.push(`${pathname}?${next.toString()}`);
    });
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        applySearch();
      }}
    >
      <input
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        placeholder="이름 또는 이메일 검색"
      />
      <button disabled={isPending}>검색</button>
    </form>
  );
}
```

여기서 `draft`는 컴포넌트 state다. 아직 확정되지 않은 입력 중 값이기 때문이다. 반면 `q`는 URL state다. 서버 조회 결과에 반영된 검색 조건이기 때문이다.

이 구분이 없으면 한 글자마다 URL이 바뀌고, history가 쌓이고, 서버 렌더링이 반복되고, 사용자는 뒤로 가기를 눌렀을 때 `k` → `ki` → `kim` 같은 입력 과정까지 되돌아가게 된다.

---

## 핵심개념 2: Server Component의 `searchParams`와 Client Component의 `useSearchParams()`는 책임이 다르다

App Router에는 query string을 읽는 대표적인 경로가 두 가지 있다.

1. `page.tsx`가 받는 `searchParams` prop
2. Client Component에서 쓰는 `useSearchParams()` hook

둘은 비슷해 보이지만 책임이 다르다.

`page.tsx`의 `searchParams`는 서버 데이터 조회의 기준으로 쓰기 좋다. 페이지가 어떤 query string으로 요청되었는지 서버에서 알고, 그 값을 정규화한 뒤 DB나 API를 호출할 수 있다.

```tsx
// app/users/page.tsx
import { Suspense } from "react";
import { parseUserListQuery } from "@/features/users/query";
import { UserFilters } from "@/features/users/user-filters";
import { UserTable } from "@/features/users/user-table";

type PageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function UsersPage({ searchParams }: PageProps) {
  const query = parseUserListQuery(await searchParams);

  return (
    <>
      <UserFilters initialQuery={query} />
      <Suspense key={query.cacheKey} fallback={<UserTableSkeleton />}>
        <UserTable query={query} />
      </Suspense>
    </>
  );
}
```

반면 `useSearchParams()`는 클라이언트 상호작용에 적합하다.

- 현재 URL 조건을 읽어 form 초기값을 맞춘다.
- 필터 버튼 클릭 시 다음 URL을 계산한다.
- query string 변경에 맞춰 active tab UI를 표시한다.
- `usePathname()`과 함께 현재 경로를 유지하며 search param만 바꾼다.

```tsx
"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

export function StatusFilter() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const current = searchParams.get("status") ?? "all";

  function setStatus(status: string) {
    const next = new URLSearchParams(searchParams);

    if (status === "all") {
      next.delete("status");
    } else {
      next.set("status", status);
    }

    next.delete("page");
    router.push(`${pathname}?${next.toString()}`);
  }

  return (
    <div>
      {["all", "active", "blocked"].map((status) => (
        <button
          key={status}
          aria-pressed={current === status}
          onClick={() => setStatus(status)}
        >
          {status}
        </button>
      ))}
    </div>
  );
}
```

주의할 점은 `useSearchParams()`가 Client Component hook이라는 것이다. 이 hook을 쓰는 순간 해당 컴포넌트는 클라이언트에서 실행된다. 그래서 서버에서 처리할 수 있는 데이터 조회와 query parsing까지 전부 Client Component로 끌고 오면 App Router의 장점을 잃는다.

나쁜 구조는 다음과 같다.

```tsx
"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

export function UsersPageClient() {
  const searchParams = useSearchParams();
  const [users, setUsers] = useState([]);

  useEffect(() => {
    fetch(`/api/users?${searchParams.toString()}`)
      .then((response) => response.json())
      .then(setUsers);
  }, [searchParams]);

  return <UserTable users={users} />;
}
```

이 방식은 모든 목록 화면을 SPA 데이터 fetching 패턴으로 되돌린다.

- 서버 렌더링 결과에 실제 데이터가 없다.
- 로딩 상태가 클라이언트 effect 뒤로 밀린다.
- API route와 page fetch의 캐시 정책이 분리된다.
- SEO나 공유 미리보기에서 의미 있는 결과를 만들기 어렵다.
- 오류 처리가 route-level `error.tsx`, `notFound()`와 자연스럽게 연결되지 않는다.

더 나은 구조는 서버가 결과셋을 가져오고, 클라이언트는 URL을 조작하는 얇은 컨트롤만 맡는 것이다.

```tsx
// app/users/page.tsx
export default async function UsersPage({ searchParams }: PageProps) {
  const query = parseUserListQuery(await searchParams);
  const usersPromise = getUsers(query);

  return (
    <main>
      <UserFilters initialQuery={query} />
      <Suspense key={query.cacheKey} fallback={<UserTableSkeleton />}>
        <UserTable usersPromise={usersPromise} />
      </Suspense>
    </main>
  );
}
```

```tsx
// features/users/user-table.tsx
export async function UserTable({
  usersPromise,
}: {
  usersPromise: Promise<UserListResult>;
}) {
  const result = await usersPromise;

  return (
    <table>
      <tbody>
        {result.items.map((user) => (
          <tr key={user.id}>
            <td>{user.name}</td>
            <td>{user.email}</td>
            <td>{user.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

이렇게 나누면 URL state는 공유 가능한 주소로 남고, 서버 데이터 조회는 서버 컴포넌트가 맡으며, 필터 UI만 필요한 만큼 클라이언트로 내려간다.

---

## 핵심개념 3: query string은 반드시 schema로 정규화한다

`searchParams`는 외부 입력이다. 사용자가 URL을 직접 고칠 수 있고, 북마크가 오래되었을 수 있으며, 잘못된 값이 들어올 수 있다.

```text
/users?page=-100
/users?page=abc
/users?status=super-admin
/users?sort=drop-table
/users?q=%20%20%20
/users?status=active&status=blocked
```

따라서 query string을 곧바로 DB 조회 조건으로 넘기면 안 된다. `searchParams`는 서버 입력으로 보고 parse, validate, normalize 단계를 거쳐야 한다.

좋은 query parser는 아래 책임을 가진다.

1. 허용된 key만 읽는다.
2. 문자열 공백을 정리한다.
3. 숫자를 범위 안으로 clamp한다.
4. enum 값은 allowlist로 제한한다.
5. 중복 값 정책을 정한다.
6. 기본값을 부여한다.
7. 캐시 key로 쓸 canonical representation을 만든다.

예시는 다음과 같다.

```ts
// features/users/query.ts
import { z } from "zod";

const StatusSchema = z.enum(["all", "active", "blocked", "invited"]);
const SortSchema = z.enum(["createdAt.desc", "createdAt.asc", "name.asc"]);

const RawUserListQuerySchema = z.object({
  q: z.string().optional(),
  status: StatusSchema.optional(),
  sort: SortSchema.optional(),
  page: z.coerce.number().int().min(1).max(500).optional(),
  pageSize: z.coerce.number().int().min(10).max(100).optional(),
});

export type UserListQuery = {
  q: string;
  status: z.infer<typeof StatusSchema>;
  sort: z.infer<typeof SortSchema>;
  page: number;
  pageSize: number;
  cacheKey: string;
};

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export function parseUserListQuery(
  searchParams: Record<string, string | string[] | undefined>,
): UserListQuery {
  const parsed = RawUserListQuerySchema.safeParse({
    q: first(searchParams.q)?.trim(),
    status: first(searchParams.status),
    sort: first(searchParams.sort),
    page: first(searchParams.page),
    pageSize: first(searchParams.pageSize),
  });

  const input = parsed.success ? parsed.data : {};

  const query = {
    q: input.q?.slice(0, 80) ?? "",
    status: input.status ?? "all",
    sort: input.sort ?? "createdAt.desc",
    page: input.page ?? 1,
    pageSize: input.pageSize ?? 20,
  };

  return {
    ...query,
    cacheKey: toUserListCacheKey(query),
  };
}

function toUserListCacheKey(query: Omit<UserListQuery, "cacheKey">) {
  const params = new URLSearchParams();

  if (query.q) params.set("q", query.q);
  if (query.status !== "all") params.set("status", query.status);
  if (query.sort !== "createdAt.desc") params.set("sort", query.sort);
  if (query.page !== 1) params.set("page", String(query.page));
  if (query.pageSize !== 20) params.set("pageSize", String(query.pageSize));

  return params.toString() || "default";
}
```

여기서 중요한 점은 parser가 단순히 타입만 맞추는 것이 아니라 "canonical query"를 만든다는 점이다.

아래 URL들은 사용자가 보기에는 다르지만 같은 의미일 수 있다.

```text
/users
/users?page=1
/users?page=1&sort=createdAt.desc
/users?status=all&page=1&sort=createdAt.desc
```

이 값들을 서로 다른 cache key로 취급하면 불필요한 렌더링과 fetch가 늘어난다. 반대로 서로 다른 의미를 같은 key로 뭉개면 잘못된 결과가 보인다. 그래서 query parser에서 기본값과 cache key를 함께 관리하는 편이 안전하다.

또 하나의 실무 포인트는 parser를 서버와 클라이언트가 공유 가능한 순수 함수로 두는 것이다. 서버는 DB 조회 전에 쓰고, 클라이언트는 active filter 표시나 다음 URL 계산에 같은 규칙을 활용할 수 있다. 단, parser 안에 DB나 `headers()`, `cookies()` 같은 서버 전용 API를 넣으면 공유가 깨진다.

---

## 핵심개념 4: 필터가 바뀌면 page를 초기화해야 한다

목록 화면에서 가장 흔한 버그 중 하나는 필터 변경 후 page를 그대로 유지하는 것이다.

사용자가 `/users?status=active&page=8`을 보고 있다고 하자. 여기서 상태 필터를 `blocked`로 바꿨는데 URL이 아래처럼 되면 문제가 생긴다.

```text
/users?status=blocked&page=8
```

blocked 사용자는 총 2페이지밖에 없을 수 있다. 그러면 사용자는 "결과 없음"을 보게 된다. 실제로 데이터가 없는 것이 아니라 page가 범위를 벗어난 것이다.

따라서 query state에는 의존 관계가 있다.

- 검색어가 바뀌면 page는 1로 돌아간다.
- 필터가 바뀌면 page는 1로 돌아간다.
- pageSize가 바뀌면 page는 1로 돌아가는 편이 안전하다.
- sort가 바뀌면 page를 유지할 수도 있고 초기화할 수도 있는데, 대부분은 1로 돌리는 편이 예측 가능하다.
- 단순 page 이동만 page를 보존한다.

이를 매번 컴포넌트에서 직접 처리하면 빠뜨리기 쉽다. 그래서 URL 업데이트 helper를 만들면 좋다.

```ts
// features/users/query-url.ts
type UserListPatch = {
  q?: string | null;
  status?: string | null;
  sort?: string | null;
  page?: number | null;
  pageSize?: number | null;
};

const RESET_PAGE_KEYS = new Set(["q", "status", "sort", "pageSize"]);

export function createUserListHref({
  pathname,
  current,
  patch,
}: {
  pathname: string;
  current: URLSearchParams;
  patch: UserListPatch;
}) {
  const next = new URLSearchParams(current);
  let shouldResetPage = false;

  for (const [key, value] of Object.entries(patch)) {
    if (value === null || value === "" || value === undefined) {
      next.delete(key);
    } else {
      next.set(key, String(value));
    }

    if (RESET_PAGE_KEYS.has(key)) {
      shouldResetPage = true;
    }
  }

  if (shouldResetPage && !("page" in patch)) {
    next.delete("page");
  }

  const query = next.toString();
  return query ? `${pathname}?${query}` : pathname;
}
```

이 helper를 쓰면 필터 컴포넌트가 정책을 반복하지 않아도 된다.

```tsx
"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { createUserListHref } from "./query-url";

export function RoleFilter() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  return (
    <select
      defaultValue={searchParams.get("role") ?? "all"}
      onChange={(event) => {
        router.push(
          createUserListHref({
            pathname,
            current: searchParams,
            patch: { role: event.target.value },
          }),
        );
      }}
    >
      <option value="all">전체</option>
      <option value="admin">관리자</option>
      <option value="member">멤버</option>
    </select>
  );
}
```

페이지네이션은 반대로 page만 바꾼다.

```tsx
<Link
  href={createUserListHref({
    pathname: "/users",
    current: searchParams,
    patch: { page: query.page + 1 },
  })}
>
  다음
</Link>
```

이런 작은 정책을 중앙화하면 QA 케이스가 크게 줄어든다.

---

## 핵심개념 5: Suspense boundary는 "전체 페이지 로딩"을 막기 위한 구조다

검색 조건이 바뀔 때마다 페이지 전체가 흔들리면 사용자는 화면이 느리다고 느낀다. App Router에서는 서버 컴포넌트가 새 query 조건으로 다시 렌더링될 수 있다. 이때 Suspense boundary를 잘못 잡으면 필터 UI까지 함께 사라진다.

나쁜 구조는 다음과 같다.

```tsx
export default async function UsersPage({ searchParams }: PageProps) {
  const query = parseUserListQuery(await searchParams);
  const result = await getUsers(query);

  return (
    <>
      <UserFilters initialQuery={query} />
      <UserTable result={result} />
      <Pagination result={result} />
    </>
  );
}
```

이 구조에서는 `getUsers()`가 느려지면 페이지 전체 렌더링이 늦어진다. 필터 UI도 늦게 나온다. 사용자는 검색 조건을 바꿨는데 화면이 통째로 멈춘 것처럼 느낄 수 있다.

더 나은 구조는 검색 컨트롤과 결과 영역을 나누는 것이다.

```tsx
export default async function UsersPage({ searchParams }: PageProps) {
  const query = parseUserListQuery(await searchParams);

  return (
    <main>
      <UserFilters initialQuery={query} />

      <Suspense key={query.cacheKey} fallback={<UserResultsSkeleton />}>
        <UserResults query={query} />
      </Suspense>
    </main>
  );
}

async function UserResults({ query }: { query: UserListQuery }) {
  const result = await getUsers(query);

  return (
    <>
      <UserTable items={result.items} />
      <Pagination page={query.page} totalPages={result.totalPages} />
    </>
  );
}
```

여기서 `key={query.cacheKey}`가 중요하다. query 조건이 바뀌었을 때 Suspense boundary가 새 결과 영역으로 전환되도록 명확한 키를 준다. 그렇지 않으면 fallback 표시가 기대와 다르게 동작하거나 이전 결과가 애매하게 남아 보일 수 있다.

다만 모든 query 변경에 무조건 skeleton을 보여 주는 것이 정답은 아니다. 검색 결과를 유지한 채 pending indicator만 작게 보여 주는 UX가 더 나을 때도 있다. 특히 데이터가 빠르게 바뀌고 사용자가 필터를 여러 번 조작하는 화면에서는 "기존 결과 유지 + 상단 진행 표시"가 더 안정적이다.

구조는 선택할 수 있지만 기준은 같아야 한다.

- 필터 컨트롤은 가능한 빨리 렌더링한다.
- 결과 영역은 query key 단위로 로딩과 오류를 분리한다.
- 느린 fetch가 필터 UI를 막지 않게 한다.
- query 변경 중 사용자가 어떤 상태인지 알 수 있어야 한다.

Client Component의 `useTransition()`도 이때 유용하다.

```tsx
"use client";

import { useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

export function SortSelect() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  return (
    <label>
      정렬
      <select
        aria-busy={isPending}
        defaultValue={searchParams.get("sort") ?? "createdAt.desc"}
        onChange={(event) => {
          const next = new URLSearchParams(searchParams);
          next.set("sort", event.target.value);
          next.delete("page");

          startTransition(() => {
            router.push(`${pathname}?${next.toString()}`);
          });
        }}
      >
        <option value="createdAt.desc">최신순</option>
        <option value="createdAt.asc">오래된순</option>
        <option value="name.asc">이름순</option>
      </select>
    </label>
  );
}
```

`useTransition()`은 서버 요청 자체를 빠르게 만들지는 않는다. 대신 URL 전환이 pending 상태라는 것을 UI가 표현할 수 있게 해 준다. 사용자는 "클릭이 먹혔는지"를 알 수 있고, 중복 클릭이나 성급한 재시도를 줄일 수 있다.

---

## 핵심개념 6: Layout은 search params를 직접 소유하면 안 된다

App Router의 layout은 페이지 전환 사이에 유지된다. 이 특성은 훌륭하지만, query string을 layout에서 직접 읽고 화면 상태를 결정하려고 하면 stale state 문제가 생긴다.

예를 들어 아래 요구사항을 생각해 보자.

- `/users?status=active`에서는 사이드바의 "활성 사용자" 메뉴가 강조되어야 한다.
- `/users?status=blocked`에서는 "차단 사용자" 메뉴가 강조되어야 한다.

이 강조 상태를 layout에서 서버 기준으로 계산하고 싶을 수 있다. 하지만 layout은 navigation마다 다시 렌더링되지 않을 수 있다. 그래서 search params처럼 자주 변하는 값은 page prop 또는 Client Component hook에서 다루는 편이 맞다.

좋은 기준은 다음과 같다.

- pathname 기반 내비게이션 강조는 layout에서 처리해도 된다.
- query string 기반 강조는 page 또는 Client Component에서 처리한다.
- layout은 query-dependent data fetch를 소유하지 않는다.
- 공통 header가 query를 알아야 한다면 작은 Client Component로 분리해 `useSearchParams()`를 읽는다.

예시는 다음과 같다.

```tsx
// app/users/layout.tsx
export default function UsersLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div>
      <UsersSectionNav />
      {children}
    </div>
  );
}
```

```tsx
// features/users/users-section-nav.tsx
"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

export function UsersSectionNav() {
  const searchParams = useSearchParams();
  const status = searchParams.get("status") ?? "all";

  return (
    <nav>
      <Link aria-current={status === "all" ? "page" : undefined} href="/users">
        전체
      </Link>
      <Link
        aria-current={status === "active" ? "page" : undefined}
        href="/users?status=active"
      >
        활성
      </Link>
      <Link
        aria-current={status === "blocked" ? "page" : undefined}
        href="/users?status=blocked"
      >
        차단
      </Link>
    </nav>
  );
}
```

이 컴포넌트는 작고 명확하다. layout 전체를 클라이언트 컴포넌트로 만들 필요가 없다. query-dependent UI만 클라이언트로 내려간다.

이 원칙은 App Router에서 매우 중요하다.

> **URL state를 읽어야 한다는 이유만으로 큰 layout이나 page 전체를 Client Component로 바꾸지 않는다. query를 읽는 가장 작은 조각만 클라이언트 경계로 분리한다.**

---

## 핵심개념 7: URL 변경 방법은 사용자 의도에 따라 고른다

Next.js에서 URL을 바꾸는 방법은 여러 가지다.

- `<Link href="...">`
- `router.push(...)`
- `router.replace(...)`
- `<Form action="...">`
- `window.history.pushState(...)`
- `window.history.replaceState(...)`

무엇을 써도 URL은 바뀔 수 있다. 하지만 브라우저 history와 접근성, prefetch, 서버 렌더링 흐름이 달라진다.

### 1) 사용자가 명시적으로 이동하는 링크라면 `<Link>`

페이지 번호, 탭, 정렬 옵션이 링크의 의미를 갖는다면 `<Link>`가 기본값이다.

```tsx
<Link href="/users?status=active">활성 사용자</Link>
<Link href="/users?page=2">2페이지</Link>
```

`<Link>`는 HTML anchor 의미를 유지하고, 새 탭 열기, 복사, 접근성, prefetch 같은 기본 탐색 동작과 잘 맞는다.

### 2) form submit으로 검색을 확정한다면 `router.push` 또는 Next Form

검색창은 사용자가 입력 후 submit하는 흐름이 자연스럽다.

```tsx
<form
  onSubmit={(event) => {
    event.preventDefault();
    router.push(createSearchHref());
  }}
>
  <input name="q" />
  <button>검색</button>
</form>
```

Next.js의 Form 컴포넌트를 활용하면 form data를 URL search params로 인코딩하는 흐름을 더 선언적으로 만들 수도 있다. 다만 복잡한 정규화, page reset, 빈 값 제거, debounce가 필요하면 직접 helper를 두는 편이 명확하다.

### 3) 사용자가 "새 상태로 이동했다"고 느껴야 하면 `push`

필터 적용, 검색 실행, 페이지 이동처럼 뒤로 가기로 이전 결과로 돌아가야 하는 동작은 `router.push`가 자연스럽다.

```tsx
router.push("/users?status=blocked");
```

### 4) 같은 작업의 중간값을 덮어쓰는 느낌이라면 `replace`

정렬 드롭다운처럼 history를 너무 많이 남기고 싶지 않은 동작은 `replace`가 더 나을 때도 있다. 특히 입력 중 자동 동기화하는 검색어에는 `replace`를 고려할 수 있다.

```tsx
router.replace("/users?q=kim");
```

하지만 `replace`를 남용하면 사용자가 뒤로 가기로 이전 필터 상태에 돌아가지 못한다. 업무 화면에서는 "검색 결과 A에서 B로 이동했다"는 history가 유용할 때가 많다. 따라서 팀 기준을 정해야 한다.

### 5) 서버 재탐색 없이 URL만 가볍게 맞추고 싶다면 native History API

Next.js는 native `window.history.pushState`와 `replaceState`가 라우터와 동기화되도록 지원한다. 서버 데이터를 다시 가져오지 않아도 되는 UI 상태라면 이 방식이 맞을 때가 있다.

예를 들어 locale switch, client-only sort preview, URL에 반영하되 서버 fetch를 즉시 유발하지 않는 임시 상태가 그렇다.

```tsx
"use client";

import { useSearchParams } from "next/navigation";

export function ClientOnlyDensityToggle() {
  const searchParams = useSearchParams();

  function setDensity(density: "compact" | "comfortable") {
    const next = new URLSearchParams(searchParams);
    next.set("density", density);

    window.history.replaceState(null, "", `?${next.toString()}`);
  }

  return (
    <button onClick={() => setDensity("compact")}>
      조밀하게 보기
    </button>
  );
}
```

단, 서버 결과셋을 바꾸는 조건에는 이 방식을 조심해야 한다. URL만 바뀌고 서버 컴포넌트 결과가 그대로라면 사용자는 주소와 화면이 불일치하는 상태를 보게 된다.

실무 기준은 다음처럼 둘 수 있다.

| 변경 방식 | 적합한 상황 |
| --- | --- |
| `<Link>` | 페이지네이션, 탭, 정렬 링크처럼 탐색 의미가 강한 상태 |
| `router.push` | 검색 실행, 필터 적용처럼 history가 필요한 상태 |
| `router.replace` | history를 쌓지 않아야 하는 보정, 자동 동기화 |
| `window.history.pushState` | 서버 재조회 없이 URL만 동기화할 client-only 상태 |
| `window.history.replaceState` | client-only 상태를 현재 history entry에 덮어쓰기 |

---

## 핵심개념 8: cache key는 정규화된 query에서 만들어야 한다

URL state가 서버 데이터 조회로 이어질 때 캐시 설계가 따라온다. 같은 query는 같은 데이터를 가져와야 하고, 다른 query는 다른 데이터를 가져와야 한다.

나쁜 패턴은 원본 query string을 그대로 cache key로 쓰는 것이다.

```ts
const result = await unstable_cache(
  () => fetchUsers(rawSearchParams),
  ["users", rawSearchParams.toString()],
)();
```

문제는 query param 순서와 기본값이다.

```text
/users?q=kim&status=active
/users?status=active&q=kim
/users?q=kim&status=active&page=1
```

이 셋은 같은 의미일 수 있지만 raw string은 다르다. 반대로 잘못 정규화하면 의미가 다른 조건을 같은 key로 묶을 수도 있다.

좋은 구조는 parser에서 만든 canonical query를 fetch key, Suspense key, logging attribute에 함께 쓰는 것이다.

```ts
export async function getUsers(query: UserListQuery) {
  return getUsersCached(query);
}

const getUsersCached = unstable_cache(
  async (query: UserListQuery) => {
    return db.user.findMany({
      where: toUserWhere(query),
      orderBy: toUserOrderBy(query.sort),
      skip: (query.page - 1) * query.pageSize,
      take: query.pageSize,
    });
  },
  ["users:list"],
  {
    tags: ["users"],
    revalidate: 60,
  },
);
```

위 코드는 예시로는 단순하지만, 실제로는 `unstable_cache`의 key 인자와 함수 인자가 어떻게 cache identity에 반영되는지 프레임워크 버전과 사용 방식에 맞춰 확인해야 한다. 중요한 것은 원칙이다.

- query parser가 의미 있는 값만 남긴다.
- 기본값은 key에서 제거하거나 일관되게 포함한다.
- 배열 필터는 정렬해서 key를 만든다.
- 날짜는 timezone 기준을 명확히 한 문자열로 만든다.
- tenantId, user role처럼 결과에 영향을 주는 서버 context도 key 또는 tag 경계에 반영한다.
- 권한별 결과가 다르면 public cache에 섞지 않는다.

특히 멀티테넌트 서비스에서는 URL query만 key에 넣으면 부족하다.

```ts
type UserListCacheScope = {
  tenantId: string;
  viewerRole: "owner" | "admin" | "member";
  query: UserListQuery;
};
```

같은 `/users?status=active`라도 tenant가 다르면 결과가 달라야 한다. viewer role에 따라 보이는 필드가 다르면 role도 경계가 된다. URL state와 서버 context를 함께 봐야 한다.

---

## 실무예시: 사용자 관리 목록을 URL state 중심으로 설계하기

이제 실제 구조를 하나로 묶어 보자. 요구사항은 다음과 같다.

- `/admin/users`
- 검색어 `q`
- 상태 `status=active|blocked|invited`
- 역할 `role=owner|admin|member`
- 정렬 `sort=createdAt.desc|name.asc`
- 페이지 `page`
- pageSize `pageSize`
- tenant별 사용자 목록
- 필터 변경 시 page 초기화
- 검색 결과 영역만 로딩
- 공유 가능한 URL

### 1) query model

```ts
// features/admin-users/query.ts
import { z } from "zod";

const Status = z.enum(["all", "active", "blocked", "invited"]);
const Role = z.enum(["all", "owner", "admin", "member"]);
const Sort = z.enum(["createdAt.desc", "createdAt.asc", "name.asc"]);

type RawSearchParams = Record<string, string | string[] | undefined>;

const Schema = z.object({
  q: z.string().optional(),
  status: Status.optional(),
  role: Role.optional(),
  sort: Sort.optional(),
  page: z.coerce.number().int().min(1).max(300).optional(),
  pageSize: z.coerce.number().int().min(10).max(100).optional(),
});

export type AdminUsersQuery = {
  q: string;
  status: z.infer<typeof Status>;
  role: z.infer<typeof Role>;
  sort: z.infer<typeof Sort>;
  page: number;
  pageSize: number;
  cacheKey: string;
};

function valueOf(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export function parseAdminUsersQuery(params: RawSearchParams): AdminUsersQuery {
  const result = Schema.safeParse({
    q: valueOf(params.q)?.trim(),
    status: valueOf(params.status),
    role: valueOf(params.role),
    sort: valueOf(params.sort),
    page: valueOf(params.page),
    pageSize: valueOf(params.pageSize),
  });

  const input = result.success ? result.data : {};

  const query = {
    q: input.q ? input.q.slice(0, 80) : "",
    status: input.status ?? "all",
    role: input.role ?? "all",
    sort: input.sort ?? "createdAt.desc",
    page: input.page ?? 1,
    pageSize: input.pageSize ?? 20,
  };

  return {
    ...query,
    cacheKey: stringifyAdminUsersQuery(query),
  };
}

export function stringifyAdminUsersQuery(
  query: Omit<AdminUsersQuery, "cacheKey">,
) {
  const params = new URLSearchParams();

  if (query.q) params.set("q", query.q);
  if (query.status !== "all") params.set("status", query.status);
  if (query.role !== "all") params.set("role", query.role);
  if (query.sort !== "createdAt.desc") params.set("sort", query.sort);
  if (query.page !== 1) params.set("page", String(query.page));
  if (query.pageSize !== 20) params.set("pageSize", String(query.pageSize));

  return params.toString() || "default";
}
```

### 2) URL update helper

```ts
// features/admin-users/query-url.ts
import type { AdminUsersQuery } from "./query";

type Patch = Partial<{
  q: string | null;
  status: AdminUsersQuery["status"] | null;
  role: AdminUsersQuery["role"] | null;
  sort: AdminUsersQuery["sort"] | null;
  page: number | null;
  pageSize: number | null;
}>;

const PAGE_RESET_FIELDS = new Set(["q", "status", "role", "sort", "pageSize"]);

export function createAdminUsersHref({
  pathname,
  current,
  patch,
}: {
  pathname: string;
  current: URLSearchParams;
  patch: Patch;
}) {
  const next = new URLSearchParams(current);
  let resetPage = false;

  for (const [key, value] of Object.entries(patch)) {
    if (value === null || value === "" || value === "all") {
      next.delete(key);
    } else {
      next.set(key, String(value));
    }

    if (PAGE_RESET_FIELDS.has(key)) {
      resetPage = true;
    }
  }

  if (resetPage && patch.page === undefined) {
    next.delete("page");
  }

  const query = next.toString();
  return query ? `${pathname}?${query}` : pathname;
}
```

### 3) page composition

```tsx
// app/admin/users/page.tsx
import { Suspense } from "react";
import { parseAdminUsersQuery } from "@/features/admin-users/query";
import { AdminUserFilters } from "@/features/admin-users/admin-user-filters";
import { AdminUserResults } from "@/features/admin-users/admin-user-results";

type PageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function AdminUsersPage({ searchParams }: PageProps) {
  const query = parseAdminUsersQuery(await searchParams);

  return (
    <main>
      <header>
        <h1>사용자 관리</h1>
      </header>

      <AdminUserFilters initialQuery={query} />

      <Suspense key={query.cacheKey} fallback={<AdminUserResultsSkeleton />}>
        <AdminUserResults query={query} />
      </Suspense>
    </main>
  );
}
```

### 4) filters

```tsx
// features/admin-users/admin-user-filters.tsx
"use client";

import { useState, useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { AdminUsersQuery } from "./query";
import { createAdminUsersHref } from "./query-url";

export function AdminUserFilters({
  initialQuery,
}: {
  initialQuery: AdminUsersQuery;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const [q, setQ] = useState(initialQuery.q);

  function navigate(patch: Parameters<typeof createAdminUsersHref>[0]["patch"]) {
    const href = createAdminUsersHref({
      pathname,
      current: searchParams,
      patch,
    });

    startTransition(() => {
      router.push(href);
    });
  }

  return (
    <section aria-busy={isPending}>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          navigate({ q });
        }}
      >
        <input
          value={q}
          onChange={(event) => setQ(event.target.value)}
          placeholder="이름, 이메일 검색"
        />
        <button>검색</button>
      </form>

      <select
        value={searchParams.get("status") ?? "all"}
        onChange={(event) => navigate({ status: event.target.value as never })}
      >
        <option value="all">전체 상태</option>
        <option value="active">활성</option>
        <option value="blocked">차단</option>
        <option value="invited">초대중</option>
      </select>

      <select
        value={searchParams.get("role") ?? "all"}
        onChange={(event) => navigate({ role: event.target.value as never })}
      >
        <option value="all">전체 역할</option>
        <option value="owner">소유자</option>
        <option value="admin">관리자</option>
        <option value="member">멤버</option>
      </select>
    </section>
  );
}
```

### 5) server results

```tsx
// features/admin-users/admin-user-results.tsx
import Link from "next/link";
import type { AdminUsersQuery } from "./query";
import { getAdminUsers } from "./service";

export async function AdminUserResults({
  query,
}: {
  query: AdminUsersQuery;
}) {
  const tenant = await requireTenantContext();
  const result = await getAdminUsers({ tenantId: tenant.id, query });

  if (result.items.length === 0) {
    return <EmptyUsers query={query} />;
  }

  return (
    <>
      <table>
        <tbody>
          {result.items.map((user) => (
            <tr key={user.id}>
              <td>{user.name}</td>
              <td>{user.email}</td>
              <td>{user.status}</td>
              <td>{user.role}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <nav>
        {query.page > 1 ? (
          <Link href={`/admin/users?${toPageQuery(query, query.page - 1)}`}>
            이전
          </Link>
        ) : null}
        {query.page < result.totalPages ? (
          <Link href={`/admin/users?${toPageQuery(query, query.page + 1)}`}>
            다음
          </Link>
        ) : null}
      </nav>
    </>
  );
}
```

이 구조의 장점은 명확하다.

- `page.tsx`는 URL을 읽고 query model을 만든다.
- 필터 UI는 query model을 표시하고 다음 URL만 계산한다.
- 서버 결과 영역은 query model과 tenant context로 데이터를 가져온다.
- Suspense boundary는 결과 영역만 감싼다.
- query parser가 기본값, 허용값, cache key를 한곳에서 관리한다.
- 필터 변경 시 page reset 정책이 helper에 들어 있다.

코드 양은 조금 늘지만, 화면이 커질수록 이 구조가 오히려 싸다. 검색 조건이 3개에서 12개로 늘어도 원칙이 유지되기 때문이다.

---

## 트레이드오프 1: 모든 검색어를 즉시 URL에 반영할 것인가, submit 후 반영할 것인가

검색 UX에서 가장 많이 갈리는 선택은 입력 즉시 URL을 바꿀지, 사용자가 submit할 때만 URL을 바꿀지다.

### 입력 즉시 반영

장점은 반응성이 좋다는 것이다. 사용자가 입력하는 즉시 결과가 바뀌고, 별도 검색 버튼이 필요 없을 수 있다.

하지만 비용도 있다.

- URL history가 과도하게 쌓일 수 있다.
- 서버 렌더링과 데이터 fetch가 많이 발생한다.
- debounce와 abort, pending UI가 필요하다.
- IME 입력 중 한글 조합 상태를 잘못 처리하면 이상한 검색이 발생한다.
- 짧은 검색어에 대해 무의미한 요청이 많아질 수 있다.

### submit 후 반영

장점은 제어가 쉽다는 것이다.

- 사용자가 검색 의도를 명확히 확정한다.
- history가 깔끔하다.
- 서버 요청 수가 줄어든다.
- page reset과 validation을 한 번에 처리하기 쉽다.

단점은 한 번 더 누르는 동작이 필요하고, 검색 자동완성처럼 즉시성 있는 경험에는 덜 맞는다.

실무에서는 화면 성격에 따라 선택한다.

- 관리자 목록, 감사 로그, 정산 내역: submit 후 반영이 안정적이다.
- 쇼핑 검색, 자동완성, 탐색형 필터: debounce 후 즉시 반영이 자연스럽다.
- 비용이 큰 검색, 복잡한 DB query: submit 후 반영을 기본으로 둔다.
- client-only 필터링: 즉시 반영해도 부담이 적다.

입력 즉시 URL 반영을 한다면 `replace`와 debounce를 함께 고려한다.

```tsx
useEffect(() => {
  const handle = window.setTimeout(() => {
    const next = new URLSearchParams(searchParams);

    if (draft.trim().length >= 2) {
      next.set("q", draft.trim());
    } else {
      next.delete("q");
    }

    next.delete("page");
    router.replace(`${pathname}?${next.toString()}`);
  }, 300);

  return () => window.clearTimeout(handle);
}, [draft, pathname, router, searchParams]);
```

이 코드는 개념 예시다. 실제로는 `searchParams` 객체 참조 변화, IME composition, 최소 검색 길이, 빈 값 처리, route transition pending 상태까지 함께 검토해야 한다. 자동 검색은 보기보다 운영 비용이 크다.

---

## 트레이드오프 2: Offset pagination과 Cursor pagination은 URL 모양이 다르다

`page=3` 방식은 이해하기 쉽다.

```text
/users?page=3&pageSize=20
```

장점은 명확하다.

- 특정 페이지로 이동하기 쉽다.
- 총 페이지 수를 보여 주기 쉽다.
- 관리자 화면과 보고서에 익숙하다.
- URL을 사람이 이해하기 좋다.

하지만 데이터가 자주 바뀌는 목록에서는 문제가 생긴다. 1페이지에 새 항목이 추가되면 3페이지의 항목 구성이 밀릴 수 있다. 큰 offset은 DB 성능에도 부담이 된다.

Cursor pagination은 다른 모양을 갖는다.

```text
/events?after=eyJjcmVhdGVkQXQiOiIyMDI2LTA3LTEw...&limit=50
```

장점은 대용량·실시간 목록에 강하다는 것이다.

- 다음 페이지 조회 성능이 안정적이다.
- 무한 스크롤과 잘 맞는다.
- 데이터 삽입이 많아도 상대적으로 덜 흔들린다.

단점도 있다.

- 특정 페이지 번호로 바로 이동하기 어렵다.
- URL이 사람이 읽기 어렵다.
- cursor에는 정렬 기준과 tie-breaker가 포함되어야 한다.
- 필터나 정렬이 바뀌면 cursor를 반드시 폐기해야 한다.

실무 기준은 다음과 같다.

| 화면 | 권장 방식 |
| --- | --- |
| 관리자 사용자 목록 | offset page |
| 정산 보고서 | offset page |
| 이벤트 로그 | cursor |
| 채팅 메시지 | cursor |
| 알림 피드 | cursor |
| 검색 결과 | 서비스 성격에 따라 선택 |

Cursor를 URL에 둘 때는 보안도 봐야 한다. cursor가 단순 base64라면 내부 ID나 timestamp가 노출될 수 있다. 민감한 정보가 들어가면 서명하거나 opaque token으로 만들어야 한다.

```ts
type CursorPayload = {
  createdAt: string;
  id: string;
  sort: "createdAt.desc";
};
```

cursor는 현재 query 조건에 묶인 값이다. `status=active`에서 받은 cursor를 `status=blocked`에 재사용하면 안 된다. 따라서 필터 변경 시 `after`, `before` 같은 cursor param은 삭제해야 한다.

---

## 트레이드오프 3: URL state와 form state를 완전히 동기화할 것인가

필터 UI를 만들 때 `value={searchParams.get(...)}`처럼 URL을 단일 source of truth로 삼는 방식이 있다. 반대로 form 내부 draft state를 두고 submit 시 URL에 반영하는 방식이 있다.

URL 단일 source of truth는 단순하다.

```tsx
const value = searchParams.get("status") ?? "all";
```

select, radio, tab처럼 클릭 즉시 확정되는 값에는 좋다.

하지만 text input에는 불편할 수 있다. 사용자가 입력하는 모든 중간값이 URL이 되거나, URL 반영 전에는 input이 제어되지 않는 문제가 생긴다.

그래서 실무에서는 상태 종류별로 나눈다.

- select/radio/toggle filter: URL을 source of truth로 둔다.
- text search input: draft state를 따로 둔다.
- date range picker: picker 내부 state를 두고 적용 버튼에서 URL 반영한다.
- 대량 checkbox 필터: 임시 선택 후 적용 버튼에서 URL 반영한다.

이 구조가 조금 복잡해 보이지만 사용자 경험은 더 좋다. 특히 날짜 범위 필터는 시작일만 고른 상태가 URL에 반영되면 의미가 불완전할 수 있다. 이런 상태는 form draft로 유지하고, 적용 버튼에서 완성된 query로 바꾸는 편이 낫다.

---

## 흔한 실수 1: `URLSearchParams`를 수정하면서 기존 값을 날린다

필터 하나를 바꿀 때 기존 query를 유지하지 않으면 사용자가 설정한 조건이 사라진다.

```ts
// 나쁜 예: status를 바꾸면서 q, sort가 사라진다.
router.push(`/users?status=${status}`);
```

좋은 방식은 현재 search params를 복사해 필요한 key만 바꾸는 것이다.

```ts
const next = new URLSearchParams(searchParams);
next.set("status", status);
next.delete("page");
router.push(`${pathname}?${next.toString()}`);
```

단, 현재 params를 무조건 다 보존하는 것도 위험할 수 있다. 더 이상 의미 없는 cursor, 잘못된 page, deprecated key는 정리해야 한다. 그래서 앞서 본 helper가 필요하다.

---

## 흔한 실수 2: query string의 배열 값을 고려하지 않는다

URLSearchParams는 같은 key를 여러 번 가질 수 있다.

```text
/users?status=active&status=blocked
```

Next.js의 `searchParams` prop에서도 값이 `string | string[] | undefined` 형태가 될 수 있다. 이때 정책을 정해야 한다.

- 첫 번째 값만 쓸 것인가
- 마지막 값만 쓸 것인가
- 배열 필터로 허용할 것인가
- 중복 값은 제거할 것인가
- 허용되지 않는 조합은 기본값으로 돌릴 것인가

다중 선택 필터라면 배열을 정식으로 지원해야 한다.

```text
/users?role=admin&role=member
```

이 경우 canonical key를 만들 때 정렬과 중복 제거를 해야 한다.

```ts
function normalizeArray(value: string | string[] | undefined) {
  const values = Array.isArray(value) ? value : value ? [value] : [];
  return [...new Set(values)].sort();
}
```

배열 필터를 지원하지 않는다면 첫 번째 값만 쓰고 나머지는 무시하는 식으로 정책을 고정한다. 중요한 것은 우연에 맡기지 않는 것이다.

---

## 흔한 실수 3: `useSearchParams()` 때문에 큰 컴포넌트를 클라이언트로 만든다

목록 page 전체를 `"use client"`로 바꾸는 순간 서버 컴포넌트의 장점이 사라진다.

나쁜 흐름은 보통 이렇다.

1. 필터 UI에서 query string을 읽어야 한다.
2. page 최상단에 `"use client"`를 붙인다.
3. 서버 데이터 fetch를 API route로 옮긴다.
4. loading, error, cache, auth 처리가 모두 클라이언트 effect 주변으로 흩어진다.

더 좋은 흐름은 query를 읽는 작은 컨트롤만 클라이언트로 분리하는 것이다.

```tsx
export default async function Page({ searchParams }: PageProps) {
  const query = parseQuery(await searchParams);

  return (
    <>
      <Filters initialQuery={query} />
      <Results query={query} />
    </>
  );
}
```

```tsx
"use client";

export function Filters({ initialQuery }: { initialQuery: Query }) {
  // useSearchParams, useRouter는 여기서만 사용
}
```

이 경계가 App Router 코드 리뷰에서 가장 중요하다.

---

## 흔한 실수 4: URL에는 q가 있는데 input에는 예전 값이 남는다

검색 input에 draft state를 두면 URL 변경과 draft state가 어긋날 수 있다. 예를 들어 사용자가 뒤로 가기를 눌러 `q=kim`에서 `q=lee`로 돌아왔는데 input은 여전히 `kim`일 수 있다.

이를 해결하려면 URL의 적용된 값이 바뀔 때 draft를 동기화해야 한다.

```tsx
const appliedQ = searchParams.get("q") ?? "";
const [draft, setDraft] = useState(appliedQ);

useEffect(() => {
  setDraft(appliedQ);
}, [appliedQ]);
```

다만 이 동기화는 사용자가 입력 중인 값을 덮어쓸 수 있다. 그래서 화면에 따라 정책이 필요하다.

- 뒤로 가기와 외부 링크 진입을 정확히 반영해야 하면 동기화한다.
- 입력 중 사용자의 draft를 보호해야 하면 submit 시점까지 동기화를 미룬다.
- 복잡한 form은 `key={query.cacheKey}`로 form을 재마운트하는 방식도 검토한다.

단순해 보이는 검색창에도 상태 전이가 있다. 이 부분을 테스트하지 않으면 브라우저 history에서 버그가 나온다.

---

## 흔한 실수 5: 정렬 기준에 tie-breaker가 없다

페이지네이션과 정렬을 함께 쓸 때 정렬 기준이 안정적이지 않으면 같은 항목이 여러 페이지에 중복되거나 누락될 수 있다.

```ts
orderBy: {
  createdAt: "desc",
}
```

`createdAt`이 같은 레코드가 많으면 DB는 같은 timestamp 안에서 순서를 보장하지 않을 수 있다. 페이지 1과 페이지 2를 조회하는 사이에 순서가 흔들리면 사용자는 이상한 목록을 본다.

좋은 정렬은 tie-breaker를 포함한다.

```ts
orderBy: [
  { createdAt: "desc" },
  { id: "desc" },
]
```

URL에는 `sort=createdAt.desc`만 보이더라도 서버의 실제 정렬 구현은 안정적인 순서를 만들어야 한다. Cursor pagination에서는 tie-breaker가 더 중요하다. cursor payload에도 `createdAt`과 `id`가 함께 들어가야 한다.

---

## 흔한 실수 6: "결과 없음"과 "잘못된 page"를 구분하지 않는다

`/users?q=zzzz`의 결과 없음과 `/users?status=active&page=999`의 결과 없음은 다르다.

첫 번째는 실제로 검색 결과가 없는 것이다. 두 번째는 page가 범위를 벗어난 것일 수 있다. 사용자에게 같은 빈 화면을 보여 주면 원인을 알기 어렵다.

운영 UX는 보통 이렇게 나눈다.

- 검색·필터 결과가 0건: 조건을 바꾸라는 empty state를 보여 준다.
- page가 totalPages보다 큼: 1페이지로 redirect하거나 마지막 페이지 링크를 제공한다.
- page 값이 잘못됨: parser에서 기본값 1로 보정한다.
- pageSize가 너무 큼: 최대값으로 clamp한다.

서버에서 total count를 구할 수 있다면 page range를 검증할 수 있다.

```ts
if (query.page > result.totalPages && result.totalPages > 0) {
  redirect(`/users?${toPageQuery(query, 1)}`);
}
```

단, redirect를 너무 쉽게 넣으면 cache와 UX가 복잡해질 수 있다. 관리자 화면에서는 "조건에 맞는 마지막 페이지가 없어 1페이지로 이동했습니다" 같은 안내가 필요할 때도 있다.

---

## 흔한 실수 7: query param 이름을 화면마다 제멋대로 만든다

한 화면은 `q`, 다른 화면은 `keyword`, 또 다른 화면은 `searchText`를 쓰면 팀 전체의 라우팅 문법이 복잡해진다.

가능하면 공통 어휘를 정하자.

- 검색어: `q`
- 페이지 번호: `page`
- 페이지 크기: `pageSize`
- 정렬: `sort`
- 시작일: `from`
- 종료일: `to`
- 상태: `status`
- 탭: `tab`

물론 도메인에 따라 `customerId`, `workspace`, `assignee`처럼 구체적인 이름이 필요할 수 있다. 중요한 것은 같은 의미에 같은 이름을 쓰는 것이다.

정렬 값도 규칙을 정하면 좋다.

```text
sort=createdAt.desc
sort=name.asc
sort=amount.desc
```

이 방식은 사람이 읽기 쉽고 확장하기도 쉽다. 다만 서버에서는 allowlist로만 받아야 한다. query string의 정렬 필드를 그대로 SQL order by에 넣으면 안 된다.

---

## 흔한 실수 8: query state를 분석·로그와 연결하지 않는다

운영에서 "사용자 목록이 느리다"는 제보를 받았을 때 query state가 로그에 남아 있지 않으면 원인 추적이 어렵다.

최소한 서버 데이터 조회 로그에는 다음이 있어야 한다.

- route: `/admin/users`
- tenantId
- normalized query cacheKey
- page, pageSize
- sort
- result count
- total count 또는 hasNextPage
- DB latency
- cache hit 여부

예시:

```ts
logger.info("admin_users.list.loaded", {
  tenantId,
  queryKey: query.cacheKey,
  page: query.page,
  pageSize: query.pageSize,
  sort: query.sort,
  itemCount: result.items.length,
  totalCount: result.totalCount,
  durationMs,
});
```

개인정보가 들어갈 수 있는 검색어 원문은 조심해야 한다. `q`에 이메일, 전화번호, 주민번호 같은 값이 들어갈 수 있다면 원문을 그대로 로그에 남기지 않는 편이 좋다. 대신 길이, 존재 여부, hash 정도만 남기는 방식을 고려한다.

URL state는 공유와 재현에 유리하지만, 그만큼 로그와 분석에도 남기 쉽다. 민감한 값을 URL에 넣지 말라는 원칙이 여기서 다시 중요해진다.

---

## 체크리스트: Next.js URL State 코드 리뷰 기준

### URL 설계

- 이 상태가 새로고침, 공유, 뒤로 가기에 의미가 있는가?
- URL에 민감한 값, 토큰, 권한 판단 값이 들어가지 않는가?
- query param 이름이 팀의 공통 어휘와 맞는가?
- 기본값이 URL에 불필요하게 붙지 않는가?
- 같은 의미의 URL이 canonical하게 정규화되는가?

### Parsing

- `searchParams`를 외부 입력으로 보고 schema validation을 하는가?
- enum 값은 allowlist로 제한하는가?
- page, pageSize는 숫자 범위가 제한되는가?
- 배열 값 또는 중복 key 정책이 명확한가?
- 잘못된 query를 500 에러가 아니라 기본값 또는 400/redirect로 처리하는가?

### Server/Client 경계

- 서버 데이터 조회는 가능한 Server Component에서 수행하는가?
- `useSearchParams()` 때문에 page 전체가 Client Component가 되지 않았는가?
- query-dependent UI만 작은 Client Component로 분리했는가?
- layout에서 search params를 소유해 stale state를 만들지 않는가?

### Navigation

- 페이지네이션과 탭은 `<Link>`로 표현 가능한가?
- 검색 실행과 필터 적용은 `push`와 `replace` 중 의도에 맞게 선택했는가?
- 필터 변경 시 page 또는 cursor를 초기화하는가?
- 검색 input의 draft state와 URL 적용 state가 어긋나지 않는가?
- IME 입력, debounce, 뒤로 가기를 테스트했는가?

### Rendering

- 결과 영역이 Suspense boundary로 분리되어 있는가?
- boundary key가 query cache key와 연결되어 있는가?
- 필터 UI가 느린 데이터 fetch에 막히지 않는가?
- 빈 결과와 잘못된 page 상태를 구분하는가?

### Data/Cache

- DB query 조건은 정규화된 query model에서 만들어지는가?
- sort는 allowlist와 tie-breaker를 갖는가?
- cache key에 query뿐 아니라 tenant, role 등 결과에 영향을 주는 서버 context가 반영되는가?
- 같은 의미의 query가 불필요하게 다른 cache entry를 만들지 않는가?
- 권한별 결과가 public cache에 섞이지 않는가?

### Observability

- normalized query key가 로그나 trace에 남는가?
- 검색어 원문처럼 민감할 수 있는 값은 로그에서 보호되는가?
- pageSize 남용, 비싼 sort, 빈 결과 급증을 관측할 수 있는가?
- 느린 query를 재현할 수 있는 URL과 서버 로그가 연결되는가?

---

## 참고 문서

- Next.js `useSearchParams`: <https://nextjs.org/docs/app/api-reference/functions/use-search-params>
- Next.js `page.js` file convention과 `searchParams`: <https://nextjs.org/docs/app/api-reference/file-conventions/page>
- Next.js `useRouter`: <https://nextjs.org/docs/app/api-reference/functions/use-router>
- Next.js `usePathname`: <https://nextjs.org/docs/app/api-reference/functions/use-pathname>
- Next.js Linking and Navigating: <https://nextjs.org/docs/app/getting-started/linking-and-navigating>
- Next.js Layout query params 주의사항: <https://nextjs.org/docs/app/api-reference/file-conventions/layout>

---

## 한줄정리

Next.js에서 검색·필터·정렬·페이지네이션을 잘 만든다는 것은 query string을 편하게 읽는 것이 아니라, **URL을 현재 데이터셋의 안정적인 주소로 정규화하고, 그 주소를 서버 조회·클라이언트 상호작용·Suspense·캐시·로그가 같은 방식으로 해석하게 만드는 것**이다.
