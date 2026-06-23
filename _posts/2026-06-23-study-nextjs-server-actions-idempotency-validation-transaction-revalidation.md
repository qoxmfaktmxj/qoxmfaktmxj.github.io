---
layout: post
title: "Next.js Server Actions 실전: Idempotency, Validation, Transaction, Revalidation으로 안전한 쓰기 흐름을 설계하는 법"
date: 2026-06-23 11:50:00 +0900
categories: [nextjs]
tags: [study, nextjs, server-actions, mutation, idempotency, validation, transaction, revalidation, app-router, security, operations]
permalink: /nextjs/2026/06/23/study-nextjs-server-actions-idempotency-validation-transaction-revalidation.html
---

## 배경: Server Actions는 "폼 submit을 편하게 만드는 기능"이 아니라 서버 쓰기 경계를 재설계하게 만드는 기능이다

Next.js App Router에서 Server Actions를 처음 접하면 매력은 아주 단순해 보인다.

- API Route를 따로 만들지 않고 서버 함수를 직접 호출할 수 있다.
- `<form action={createPost}>`처럼 HTML 폼과 자연스럽게 연결된다.
- 클라이언트 컴포넌트에서 `fetch('/api/...')`를 반복하지 않아도 된다.
- 저장 후 `revalidatePath()`나 `redirect()`를 바로 호출할 수 있다.
- 서버에만 있어야 하는 DB client, secret, 권한 검증 로직을 브라우저 번들에서 떼어낼 수 있다.

그래서 많은 팀이 Server Actions를 "Route Handler를 줄여 주는 문법" 정도로 도입한다. 작은 데모에서는 이 판단이 맞아 보인다. 글 작성 폼을 만들고, `formData`를 받아 DB에 저장하고, 목록 페이지를 재검증하면 끝이다.

하지만 실무의 쓰기 흐름은 그렇게 단순하지 않다.

- 사용자가 저장 버튼을 두 번 눌러 같은 주문이 중복 생성된다.
- 브라우저가 재시도한 요청과 사용자의 재클릭이 섞여 같은 결제가 두 번 처리된다.
- 클라이언트 검증은 통과했지만 서버 검증이 약해 잘못된 enum 값이 DB에 들어간다.
- 권한 검증은 했지만 트랜잭션 밖에서 조회한 데이터가 저장 직전에 바뀐다.
- 저장은 성공했는데 `revalidatePath()`가 누락되어 사용자는 예전 목록을 본다.
- `redirect()`를 먼저 호출해 후속 로깅, 감사 이벤트, 캐시 무효화가 실행되지 않는다.
- Server Action 내부에서 외부 API를 호출했는데 timeout과 재시도 정책이 없어 요청이 매달린다.
- 낙관적 UI는 성공처럼 보였지만 서버에서 실패했고, 에러 복구 UX가 없다.
- action 함수가 여러 화면에서 재사용되면서 어떤 페이지를 재검증해야 하는지 불명확해진다.

즉 Server Actions는 단순히 API endpoint 파일을 줄이는 기능이 아니다.

> **Server Actions의 본질은 사용자 인터랙션에서 시작한 쓰기 요청을 서버 함수 경계로 끌어오고, 그 경계 안에서 검증, 권한, 중복 방지, 트랜잭션, 캐시 무효화, 리다이렉트, 에러 매핑을 일관되게 처리하게 만드는 것이다.**

이 글은 "Server Action을 어떻게 선언하는가"를 설명하는 초급 글이 아니다. 중급 이상 개발자를 기준으로 실제 서비스에서 안전한 쓰기 흐름을 만들기 위해 무엇을 고정해야 하는지 정리한다.

1. Server Actions를 Route Handler와 어떻게 구분해서 써야 하는가
2. 서버 검증과 권한 검증을 어떤 순서로 배치해야 하는가
3. idempotency key 없이 쓰기 요청을 받으면 왜 중복 생성이 생기는가
4. DB transaction, 외부 API, cache revalidation은 어떤 순서로 묶어야 하는가
5. `revalidatePath`, `revalidateTag`, `redirect`는 어디에서 호출해야 사고가 적은가
6. 낙관적 UI, 에러 반환, toast, form state는 어떤 책임을 나눠야 하는가
7. 실무에서 자주 깨지는 패턴과 배포 전 체크리스트는 무엇인가

결론부터 말하면 이렇다.

**Server Actions는 "서버에서 실행되는 함수"라서 안전한 것이 아니다. 안전한 쓰기 흐름은 action 경계 안에 validation, authorization, idempotency, transaction, revalidation, error mapping을 명시적으로 배치할 때 만들어진다.**

---

## 먼저 큰 그림: 쓰기 흐름은 "입력 → 의도 → 변경 → 관측 가능한 결과"로 나눠야 한다

쓰기 기능을 구현할 때 가장 흔한 실수는 UI 이벤트와 DB 변경을 바로 연결하는 것이다.

```tsx
// app/posts/new/actions.ts
"use server";

export async function createPost(formData: FormData) {
  await db.post.create({
    data: {
      title: String(formData.get("title")),
      body: String(formData.get("body")),
    },
  });

  revalidatePath("/posts");
  redirect("/posts");
}
```

예제 코드로는 나쁘지 않다. 하지만 운영 코드로는 중요한 질문들이 빠져 있다.

- 사용자는 누구인가
- 이 사용자는 이 workspace에 글을 만들 권한이 있는가
- title과 body는 서버 기준으로 유효한가
- 같은 form submit이 두 번 들어오면 어떻게 할 것인가
- DB 저장과 감사 로그는 같은 transaction에 들어가야 하는가
- 저장 후 어떤 cache key를 무효화해야 하는가
- 실패하면 사용자에게 어떤 메시지를 줄 것인가
- 예상 가능한 실패와 시스템 장애를 어떻게 구분할 것인가

그래서 Server Action은 단순히 "DB를 호출하는 곳"이 아니라 아래 흐름의 조립 지점으로 봐야 한다.

1. **입력 수신**: `FormData` 또는 typed argument를 받는다.
2. **입력 정규화**: 문자열 trim, 숫자 변환, checkbox 처리, 빈 값 처리.
3. **서버 검증**: schema validation, business validation, cross-field validation.
4. **인증 확인**: 현재 사용자, session, tenant, role을 확정한다.
5. **권한 확인**: 이 리소스에 이 변경을 할 수 있는지 확인한다.
6. **중복 방지**: idempotency key 또는 unique constraint로 재시도를 흡수한다.
7. **변경 실행**: DB transaction 안에서 상태 변경과 outbox, audit log를 함께 처리한다.
8. **후속 처리 예약**: 외부 API 호출이 필요하면 transaction 밖으로 분리하거나 outbox로 넘긴다.
9. **캐시 무효화**: 변경된 read model에 맞춰 path 또는 tag를 재검증한다.
10. **결과 반환**: field error, form error, success payload, redirect를 일관되게 선택한다.

이 순서를 코드 리뷰 기준으로 삼으면 Server Actions가 커져도 흐름이 무너지지 않는다.

---

## 핵심개념 1: Server Action은 공개 API가 아니지만, 신뢰 경계는 여전히 서버 입력이다

Server Actions는 브라우저에서 직접 URL을 설계하지 않아도 호출된다. 그래서 "외부 API가 아니니 조금 느슨해도 되지 않을까"라는 착각이 생긴다.

그렇게 보면 위험하다. Server Action은 결국 사용자의 브라우저에서 시작한 요청을 서버가 처리하는 입력 경계다.

- 클라이언트 검증은 우회될 수 있다.
- hidden input 값은 사용자가 바꿀 수 있다.
- select option에 없던 enum 값도 직접 보낼 수 있다.
- client component에서 넘긴 인자는 신뢰할 수 없다.
- tenantId, userId, role 같은 보안 핵심 값은 클라이언트에서 받으면 안 된다.

따라서 action의 첫 번째 원칙은 명확하다.

> **보안상 중요한 값은 클라이언트 입력에서 받지 말고, 서버의 session, cookie, route context, DB 조회로 확정한다.**

예를 들어 아래 코드는 편해 보이지만 위험하다.

```tsx
// 나쁜 예: userId와 workspaceId를 클라이언트에서 받는다.
<form action={createPost}>
  <input type="hidden" name="userId" value={user.id} />
  <input type="hidden" name="workspaceId" value={workspace.id} />
  <input name="title" />
  <button type="submit">저장</button>
</form>
```

```ts
"use server";

export async function createPost(formData: FormData) {
  const userId = String(formData.get("userId"));
  const workspaceId = String(formData.get("workspaceId"));

  await db.post.create({
    data: {
      userId,
      workspaceId,
      title: String(formData.get("title")),
    },
  });
}
```

사용자가 hidden input을 바꿔 다른 workspace에 글을 만들 수 있는지 검증해야 한다. 좋은 흐름은 서버에서 사용자와 workspace 접근 권한을 다시 확정하는 것이다.

```ts
"use server";

import { z } from "zod";
import { revalidateTag } from "next/cache";
import { redirect } from "next/navigation";

const CreatePostInput = z.object({
  workspaceSlug: z.string().min(1).max(80),
  title: z.string().trim().min(1).max(120),
  body: z.string().trim().min(1).max(20_000),
});

export async function createPost(formData: FormData) {
  const parsed = CreatePostInput.safeParse({
    workspaceSlug: formData.get("workspaceSlug"),
    title: formData.get("title"),
    body: formData.get("body"),
  });

  if (!parsed.success) {
    return {
      ok: false,
      fieldErrors: parsed.error.flatten().fieldErrors,
    };
  }

  const session = await requireSession();
  const workspace = await requireWorkspaceAccess({
    userId: session.user.id,
    slug: parsed.data.workspaceSlug,
    permission: "post:create",
  });

  const post = await db.post.create({
    data: {
      workspaceId: workspace.id,
      authorId: session.user.id,
      title: parsed.data.title,
      body: parsed.data.body,
    },
  });

  revalidateTag(`workspace:${workspace.id}:posts`);
  redirect(`/workspaces/${workspace.slug}/posts/${post.id}`);
}
```

여기서 `workspaceSlug`는 routing hint일 뿐이다. 실제 저장에는 서버가 조회한 `workspace.id`를 쓴다. 이 차이를 지키는 것만으로도 많은 권한 사고를 줄일 수 있다.

---

## 핵심개념 2: validation은 "폼 입력 검증"과 "도메인 불변식 검증"으로 나눠야 한다

Server Action에서 zod 같은 schema validator를 붙이면 검증이 끝난 것처럼 느껴질 수 있다. 하지만 실무 검증은 두 층이다.

첫 번째는 **입력 형태 검증**이다.

- 필수 값인가
- 문자열 길이가 적절한가
- 숫자 범위가 맞는가
- 날짜 형식이 맞는가
- enum 값이 허용 목록 안에 있는가

두 번째는 **도메인 불변식 검증**이다.

- 이미 발행된 글은 제목을 바꿀 수 있는가
- 결제 완료 주문은 배송지 수정이 가능한가
- 휴가 신청 기간이 회사 정책과 충돌하지 않는가
- 같은 이름의 프로젝트를 같은 workspace 안에서 만들 수 있는가
- 현재 사용자의 role로 이 상태 전이를 수행할 수 있는가

입력 형태 검증은 action 초반에 빠르게 처리하는 편이 좋다. 반면 도메인 불변식은 대개 DB의 현재 상태가 필요하므로 권한 확인과 transaction 가까이에 둬야 한다.

```ts
const UpdatePostInput = z.object({
  postId: z.string().uuid(),
  title: z.string().trim().min(1).max(120),
  body: z.string().trim().min(1).max(20_000),
  expectedVersion: z.coerce.number().int().nonnegative(),
});

export async function updatePost(formData: FormData) {
  const input = parseActionInput(UpdatePostInput, formData);
  if (!input.ok) return input.error;

  const session = await requireSession();

  const result = await db.$transaction(async (tx) => {
    const post = await tx.post.findUnique({
      where: { id: input.data.postId },
      select: {
        id: true,
        workspaceId: true,
        status: true,
        version: true,
      },
    });

    if (!post) {
      return actionError("NOT_FOUND", "글을 찾을 수 없습니다.");
    }

    await requirePermissionTx(tx, {
      userId: session.user.id,
      workspaceId: post.workspaceId,
      permission: "post:update",
    });

    if (post.status === "PUBLISHED") {
      return actionError("INVALID_STATE", "발행된 글은 편집할 수 없습니다.");
    }

    if (post.version !== input.data.expectedVersion) {
      return actionError("CONFLICT", "다른 사용자가 먼저 수정했습니다. 새로고침 후 다시 시도해 주세요.");
    }

    const updated = await tx.post.update({
      where: { id: post.id },
      data: {
        title: input.data.title,
        body: input.data.body,
        version: { increment: 1 },
      },
      select: { id: true, workspaceId: true },
    });

    await tx.auditLog.create({
      data: {
        workspaceId: post.workspaceId,
        actorId: session.user.id,
        action: "post.update",
        targetId: post.id,
      },
    });

    return { ok: true as const, post: updated };
  });

  if (!result.ok) return result;

  revalidateTag(`workspace:${result.post.workspaceId}:posts`);
  revalidateTag(`post:${result.post.id}`);

  return { ok: true };
}
```

이 예시에서 중요한 점은 `expectedVersion`이다. 협업 화면에서 두 사용자가 같은 글을 동시에 편집하면 마지막 저장이 앞선 저장을 조용히 덮어쓸 수 있다. version check는 이런 lost update를 막는 가장 단순한 장치다.

---

## 핵심개념 3: idempotency는 "버튼 비활성화"가 아니라 서버의 중복 처리 계약이다

프론트엔드에서 `isSubmitting`으로 버튼을 비활성화하는 것은 좋은 UX다. 하지만 그것만으로 중복 처리를 보장할 수는 없다.

중복 요청은 여러 경로로 생긴다.

- 사용자가 브라우저 뒤로가기 후 다시 제출한다.
- 모바일 네트워크에서 요청이 timeout처럼 보였고 사용자가 재시도한다.
- 브라우저 또는 프록시가 연결 문제로 같은 요청을 다시 보낸다.
- optimistic UI 실패 복구 과정에서 같은 action을 다시 호출한다.
- 사용자가 두 탭에서 같은 폼을 열어 제출한다.
- JavaScript가 느리게 로드되어 버튼 비활성화가 늦게 적용된다.

쓰기 요청이 "한 번만 실행되어야 하는 의미"를 가진다면 서버가 idempotency를 책임져야 한다. 대표적인 예시는 결제, 주문 생성, 초대 메일 발송, 포인트 지급, 파일 처리 job 생성이다.

가장 실용적인 방식은 form마다 `idempotencyKey`를 만들고, 서버에서 unique constraint로 흡수하는 것이다.

```tsx
// app/orders/new/page.tsx
import { randomUUID } from "crypto";
import { createOrder } from "./actions";

export default function NewOrderPage() {
  const idempotencyKey = randomUUID();

  return (
    <form action={createOrder}>
      <input type="hidden" name="idempotencyKey" value={idempotencyKey} />
      <input name="productId" />
      <input name="quantity" type="number" min="1" />
      <button type="submit">주문</button>
    </form>
  );
}
```

```ts
const CreateOrderInput = z.object({
  idempotencyKey: z.string().uuid(),
  productId: z.string().uuid(),
  quantity: z.coerce.number().int().positive().max(100),
});

export async function createOrder(formData: FormData) {
  const input = parseActionInput(CreateOrderInput, formData);
  if (!input.ok) return input.error;

  const session = await requireSession();

  const result = await db.$transaction(async (tx) => {
    const existing = await tx.idempotencyKey.findUnique({
      where: {
        userId_key: {
          userId: session.user.id,
          key: input.data.idempotencyKey,
        },
      },
      include: { order: true },
    });

    if (existing?.order) {
      return { ok: true as const, orderId: existing.order.id, reused: true };
    }

    const order = await tx.order.create({
      data: {
        userId: session.user.id,
        productId: input.data.productId,
        quantity: input.data.quantity,
        status: "PENDING",
      },
    });

    await tx.idempotencyKey.create({
      data: {
        userId: session.user.id,
        key: input.data.idempotencyKey,
        orderId: order.id,
      },
    });

    await tx.outbox.create({
      data: {
        topic: "order.created",
        aggregateId: order.id,
        payload: {
          orderId: order.id,
          userId: session.user.id,
        },
      },
    });

    return { ok: true as const, orderId: order.id, reused: false };
  });

  revalidateTag(`user:${session.user.id}:orders`);
  redirect(`/orders/${result.orderId}`);
}
```

실무에서는 더 단단하게 만들기 위해 아래를 함께 고려한다.

- key scope는 전역이 아니라 보통 `userId + key`, `tenantId + key`, `operation + key`로 잡는다.
- key 보관 기간을 정한다. 결제성 요청은 길게, 단순 생성 요청은 짧게 가져갈 수 있다.
- 같은 key로 다른 payload가 들어오면 409 conflict로 처리한다.
- key record와 실제 생성 record를 같은 transaction에 묶는다.
- 외부 결제 API도 자체 idempotency key를 지원하면 같은 키를 전달한다.

idempotency는 코드 몇 줄의 문제가 아니라 "같은 의도를 가진 요청을 여러 번 받아도 결과가 하나로 수렴한다"는 서버 계약이다.

---

## 핵심개념 4: transaction 안에는 DB 일관성을, transaction 밖에는 외부 부작용을 둔다

Server Action은 서버 함수라서 DB 저장, 메일 발송, Slack 알림, 검색 색인 갱신, 캐시 재검증을 한곳에 쓰기 쉽다. 하지만 모든 부작용을 한 함수에 줄줄이 넣으면 장애 복구가 어려워진다.

특히 조심해야 할 것은 transaction 안에서 외부 API를 호출하는 패턴이다.

```ts
// 위험한 예: DB transaction 안에서 외부 메일 API를 기다린다.
await db.$transaction(async (tx) => {
  const invite = await tx.invite.create({ data });
  await emailClient.sendInvite(invite.email);
  return invite;
});
```

이 코드는 다음 문제가 있다.

- 메일 API가 느리면 DB lock 보유 시간이 길어진다.
- 메일 발송은 성공했는데 transaction commit이 실패하면 복구가 애매하다.
- transaction이 retry되면 메일이 중복 발송될 수 있다.
- 외부 장애가 DB 쓰기 경로 전체를 막는다.

더 안전한 기본값은 transaction 안에서 "보내야 한다"는 사실만 outbox에 기록하고, 실제 외부 호출은 worker가 처리하는 것이다.

```ts
await db.$transaction(async (tx) => {
  const invite = await tx.invite.create({
    data: {
      workspaceId,
      email,
      role,
      invitedById: session.user.id,
    },
  });

  await tx.outbox.create({
    data: {
      topic: "invite.created",
      aggregateId: invite.id,
      payload: {
        inviteId: invite.id,
        workspaceId,
        email,
      },
    },
  });

  await tx.auditLog.create({
    data: {
      workspaceId,
      actorId: session.user.id,
      action: "invite.create",
      targetId: invite.id,
    },
  });

  return invite;
});
```

이렇게 하면 DB 상태와 "발송해야 할 이벤트"가 같은 commit 경계를 가진다. worker는 outbox를 읽어 메일을 보내고, 실패하면 재시도한다. 재시도 가능해야 하므로 worker 쪽에서도 idempotency key 또는 provider message id를 관리하는 편이 좋다.

물론 모든 서비스가 outbox worker를 갖춰야 하는 것은 아니다. 작은 제품에서는 action 종료 후 transaction 밖에서 외부 호출을 해도 된다. 다만 그 경우에도 다음을 명시해야 한다.

- 외부 호출 실패가 사용자 요청 실패로 이어져야 하는가
- 실패했을 때 재시도할 방법이 있는가
- 중복 호출이 발생해도 괜찮은가
- 외부 호출 timeout은 몇 초인가
- 사용자에게 성공으로 보여 준 뒤 후속 처리 실패를 어떻게 알릴 것인가

핵심 기준은 단순하다.

> **DB 일관성에 필요한 변경은 transaction에 넣고, 느리거나 재시도 가능한 외부 부작용은 outbox 또는 transaction 밖으로 분리한다.**

---

## 핵심개념 5: revalidation은 저장 이후의 "읽기 모델 동기화"다

Server Actions에서 `revalidatePath()`와 `revalidateTag()`는 편리하다. 하지만 편리한 만큼 과하게 쓰거나 누락하기 쉽다.

캐시 무효화를 제대로 하려면 먼저 읽기 모델을 알아야 한다.

- 이 변경이 어떤 목록에 나타나는가
- 어떤 상세 페이지에 영향을 주는가
- 어떤 sidebar count, dashboard card, metadata에 반영되는가
- tenant, locale, role에 따라 cache key가 분리되어 있는가
- 같은 데이터를 여러 route에서 읽는가

단순한 서비스에서는 path 기반이 충분하다.

```ts
revalidatePath("/posts");
revalidatePath(`/posts/${post.id}`);
```

하지만 데이터가 여러 화면에서 공유되면 tag 기반이 더 안정적이다.

```ts
async function getWorkspacePosts(workspaceId: string) {
  return unstable_cache(
    async () => db.post.findMany({ where: { workspaceId } }),
    ["workspace-posts", workspaceId],
    { tags: [`workspace:${workspaceId}:posts`] }
  )();
}
```

```ts
revalidateTag(`workspace:${workspaceId}:posts`);
revalidateTag(`post:${postId}`);
```

여기서 중요한 것은 tag 이름 규칙이다. 팀마다 즉흥적으로 tag를 만들면 나중에 어떤 action이 어떤 read model을 무효화하는지 추적하기 어렵다. 보통은 아래처럼 resource 중심으로 잡는 편이 낫다.

- `tenant:{tenantId}:posts`
- `workspace:{workspaceId}:posts`
- `post:{postId}`
- `user:{userId}:notifications`
- `dashboard:{workspaceId}:summary`

revalidation을 설계할 때 흔한 실수는 "상세 페이지만" 무효화하는 것이다. 글 제목을 바꾸면 상세 페이지뿐 아니라 목록, 검색 결과, breadcrumb, 최근 활동, Open Graph metadata가 모두 영향을 받을 수 있다.

반대로 너무 넓게 무효화하는 것도 문제다.

```ts
// 편하지만 비용이 크다.
revalidatePath("/", "layout");
```

서비스 규모가 작을 때는 문제없지만, 대시보드와 마케팅 페이지와 관리자 페이지가 모두 같은 layout 아래에 있으면 불필요한 재생성이 커진다. 그래서 실무에서는 action마다 "변경한 write model"과 "무효화할 read model"을 리뷰해야 한다.

---

## 핵심개념 6: redirect는 반환이 아니라 throw에 가깝게 생각해야 한다

Server Action에서 `redirect()`를 호출하면 이후 코드는 실행되지 않는다고 보는 편이 안전하다. 따라서 순서가 중요하다.

```ts
// 나쁜 예: redirect 이후 코드는 실행되지 않는다.
export async function publishPost(formData: FormData) {
  const post = await publish(formData);

  redirect(`/posts/${post.id}`);

  await audit("post.publish", post.id);
  revalidateTag(`post:${post.id}`);
}
```

좋은 순서는 보통 아래다.

1. 입력 검증
2. 인증과 권한 확인
3. DB transaction
4. transaction 밖 후속 처리 예약 또는 lightweight side effect
5. cache revalidation
6. redirect 또는 success 반환

```ts
export async function publishPost(formData: FormData) {
  const input = parseActionInput(PublishPostInput, formData);
  if (!input.ok) return input.error;

  const session = await requireSession();

  const post = await db.$transaction(async (tx) => {
    const post = await requireEditablePostTx(tx, input.data.postId, session.user.id);

    if (post.status !== "DRAFT") {
      throw new ActionDomainError("INVALID_STATE", "초안 상태의 글만 발행할 수 있습니다.");
    }

    const published = await tx.post.update({
      where: { id: post.id },
      data: {
        status: "PUBLISHED",
        publishedAt: new Date(),
      },
      select: {
        id: true,
        workspaceId: true,
        slug: true,
      },
    });

    await tx.auditLog.create({
      data: {
        workspaceId: published.workspaceId,
        actorId: session.user.id,
        action: "post.publish",
        targetId: published.id,
      },
    });

    return published;
  });

  revalidateTag(`workspace:${post.workspaceId}:posts`);
  revalidateTag(`post:${post.id}`);

  redirect(`/posts/${post.slug}`);
}
```

에러 처리도 `redirect`와 섞을 때 주의해야 한다. `try/catch`로 action 전체를 감싸고 모든 에러를 `{ ok: false }`로 바꾸면 `redirect()`까지 잡아 버릴 수 있다. 따라서 예상 가능한 도메인 에러만 변환하고, framework control flow는 그대로 통과시키는 구조가 필요하다.

---

## 실무예시: 초대 기능을 Server Action으로 설계하기

이제 하나의 기능을 기준으로 전체 흐름을 묶어 보자. 예시는 workspace 초대다.

요구사항은 다음과 같다.

- workspace 관리자만 초대할 수 있다.
- 이메일은 소문자로 정규화한다.
- 같은 workspace에 이미 멤버인 사용자는 초대할 수 없다.
- 이미 대기 중인 초대가 있으면 새로 만들지 않고 기존 초대를 재사용한다.
- 초대 생성과 감사 로그, outbox 이벤트는 같은 transaction에 묶는다.
- 성공 후 멤버 관리 목록을 재검증한다.
- 사용자는 validation error를 필드별로 볼 수 있어야 한다.

```ts
"use server";

import { z } from "zod";
import { revalidateTag } from "next/cache";

const InviteInput = z.object({
  workspaceSlug: z.string().min(1).max(80),
  email: z.string().trim().email().transform((value) => value.toLowerCase()),
  role: z.enum(["ADMIN", "MEMBER", "VIEWER"]),
  idempotencyKey: z.string().uuid(),
});

type InviteState =
  | { ok: true; inviteId: string; reused: boolean }
  | { ok: false; formError?: string; fieldErrors?: Record<string, string[]> };

export async function inviteMember(_: InviteState | null, formData: FormData): Promise<InviteState> {
  const parsed = InviteInput.safeParse({
    workspaceSlug: formData.get("workspaceSlug"),
    email: formData.get("email"),
    role: formData.get("role"),
    idempotencyKey: formData.get("idempotencyKey"),
  });

  if (!parsed.success) {
    return {
      ok: false,
      fieldErrors: parsed.error.flatten().fieldErrors,
    };
  }

  const session = await requireSession();

  try {
    const result = await db.$transaction(async (tx) => {
      const workspace = await tx.workspace.findUnique({
        where: { slug: parsed.data.workspaceSlug },
        select: { id: true, slug: true },
      });

      if (!workspace) {
        return { ok: false as const, formError: "워크스페이스를 찾을 수 없습니다." };
      }

      await requirePermissionTx(tx, {
        userId: session.user.id,
        workspaceId: workspace.id,
        permission: "member:invite",
      });

      const member = await tx.workspaceMember.findUnique({
        where: {
          workspaceId_email: {
            workspaceId: workspace.id,
            email: parsed.data.email,
          },
        },
      });

      if (member) {
        return { ok: false as const, formError: "이미 워크스페이스에 속한 사용자입니다." };
      }

      const existingKey = await tx.idempotencyKey.findUnique({
        where: {
          userId_key: {
            userId: session.user.id,
            key: parsed.data.idempotencyKey,
          },
        },
      });

      if (existingKey?.resultId) {
        return { ok: true as const, inviteId: existingKey.resultId, reused: true, workspaceId: workspace.id };
      }

      const existingInvite = await tx.invite.findFirst({
        where: {
          workspaceId: workspace.id,
          email: parsed.data.email,
          status: "PENDING",
        },
        select: { id: true },
      });

      const invite =
        existingInvite ??
        (await tx.invite.create({
          data: {
            workspaceId: workspace.id,
            email: parsed.data.email,
            role: parsed.data.role,
            invitedById: session.user.id,
            status: "PENDING",
          },
          select: { id: true },
        }));

      await tx.idempotencyKey.create({
        data: {
          userId: session.user.id,
          key: parsed.data.idempotencyKey,
          operation: "invite-member",
          resultId: invite.id,
        },
      });

      await tx.auditLog.create({
        data: {
          workspaceId: workspace.id,
          actorId: session.user.id,
          action: "member.invite",
          targetId: invite.id,
          metadata: {
            email: parsed.data.email,
            role: parsed.data.role,
          },
        },
      });

      await tx.outbox.create({
        data: {
          topic: "invite.created",
          aggregateId: invite.id,
          payload: {
            inviteId: invite.id,
            workspaceId: workspace.id,
            email: parsed.data.email,
          },
        },
      });

      return { ok: true as const, inviteId: invite.id, reused: Boolean(existingInvite), workspaceId: workspace.id };
    });

    if (!result.ok) return result;

    revalidateTag(`workspace:${result.workspaceId}:members`);
    revalidateTag(`workspace:${result.workspaceId}:invites`);

    return {
      ok: true,
      inviteId: result.inviteId,
      reused: result.reused,
    };
  } catch (error) {
    reportActionError(error, {
      action: "inviteMember",
      userId: session.user.id,
    });

    return {
      ok: false,
      formError: "초대 처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    };
  }
}
```

이 예시는 코드가 길다. 하지만 길어진 이유가 단순한 장황함은 아니다. 운영에서 필요한 경계가 들어가 있다.

- 클라이언트 입력은 schema로 검증한다.
- 사용자와 workspace 권한은 서버에서 확정한다.
- 같은 사용자의 같은 요청 key는 한 번만 결과를 만든다.
- 이미 존재하는 pending invite는 재사용한다.
- 감사 로그와 outbox는 DB 변경과 같은 transaction에 있다.
- 메일 발송 자체는 action에서 직접 하지 않는다.
- 관련 목록 cache tag만 좁게 무효화한다.
- 예상 가능한 실패는 사용자 메시지로 반환하고, 예상 밖 장애는 기록한다.

이 정도의 구조를 모든 action에 똑같이 붙이라는 뜻은 아니다. 하지만 결제, 초대, 권한 변경, 발행, 삭제처럼 되돌리기 어려운 변경에는 이 수준의 설계가 필요하다.

---

## 트레이드오프: Server Actions와 Route Handlers를 어떻게 나눌 것인가

Server Actions가 있다고 해서 Route Handlers가 사라지는 것은 아니다. 두 도구는 쓰임이 다르다.

Server Actions가 잘 맞는 경우는 다음과 같다.

- React UI에서 시작하는 폼 제출 또는 버튼 액션이다.
- action 결과가 바로 같은 화면의 form state, toast, redirect로 이어진다.
- 인증된 사용자의 session context가 중요하다.
- 외부 클라이언트가 호출할 공개 API가 아니다.
- 변경 후 Next.js cache revalidation이 필요하다.

Route Handlers가 더 맞는 경우도 많다.

- 모바일 앱, 외부 서비스, webhook, batch job이 호출한다.
- HTTP method, status code, header, streaming response를 명확히 다뤄야 한다.
- 공개 API로 versioning, rate limit, API key 인증이 필요하다.
- 파일 업로드, 다운로드, SSE, webhook signature 검증처럼 HTTP 경계가 핵심이다.
- React 렌더링 흐름과 독립적으로 재사용되어야 한다.

중요한 것은 "비즈니스 로직을 어디에 둘 것인가"다. action과 route handler가 같은 도메인 변경을 각각 직접 구현하면 금방 불일치가 생긴다.

좋은 구조는 보통 세 층이다.

```txt
app/.../actions.ts          UI에서 호출하는 얇은 action adapter
app/api/.../route.ts        외부 HTTP 요청을 받는 route adapter
domain/.../commands.ts      검증된 command를 실행하는 도메인 서비스
```

Server Action은 `FormData`를 검증하고 session을 확인한 뒤 domain command를 호출한다. Route Handler는 JSON body와 API 인증을 검증한 뒤 같은 command를 호출한다. 이렇게 하면 쓰기 규칙은 한곳에 남고, 입구만 달라진다.

단, domain command에 Next.js 전용 `revalidateTag()`나 `redirect()`를 직접 넣는 것은 피하는 편이 좋다. 그러면 CLI job이나 worker에서도 해당 command를 재사용하기 어려워진다. 도메인 command는 "무엇이 바뀌었는지"를 event나 result로 반환하고, action adapter가 그 결과를 보고 revalidation과 redirect를 처리하는 구조가 더 오래 간다.

---

## 트레이드오프: form action, useActionState, optimistic UI 중 무엇을 선택할 것인가

Server Actions는 UI 연결 방식도 여러 가지다.

가장 단순한 방식은 form action이다.

```tsx
<form action={createPost}>
  <input name="title" />
  <button type="submit">저장</button>
</form>
```

이 방식은 progressive enhancement에 강하다. JavaScript가 늦게 로드되어도 기본 form submit으로 동작할 수 있고, 저장 후 redirect되는 화면에 잘 맞는다. 대신 field error를 섬세하게 보여 주려면 추가 상태 관리가 필요하다.

필드 에러와 form state가 중요하면 `useActionState` 계열 패턴이 잘 맞는다.

```tsx
"use client";

import { useActionState } from "react";
import { inviteMember } from "./actions";

const initialState = { ok: false as const };

export function InviteForm() {
  const [state, action, pending] = useActionState(inviteMember, initialState);

  return (
    <form action={action}>
      <input name="email" aria-invalid={Boolean(state.fieldErrors?.email)} />
      {state.fieldErrors?.email?.map((message) => (
        <p key={message}>{message}</p>
      ))}
      <button disabled={pending}>초대</button>
      {state.formError ? <p>{state.formError}</p> : null}
    </form>
  );
}
```

낙관적 UI는 사용자가 자주 반복하는 가벼운 변경에 적합하다.

- 체크리스트 완료
- 좋아요
- 알림 읽음 처리
- 간단한 정렬 순서 변경

하지만 결제, 권한 변경, 삭제, 발행처럼 되돌리기 어려운 작업에 무리한 낙관적 UI를 적용하면 실패 복구가 더 복잡해진다. 이 경우에는 pending state를 명확히 보여 주고, 서버 성공 후 화면을 갱신하는 편이 낫다.

선택 기준은 이렇게 잡을 수 있다.

- 저장 후 다른 페이지로 이동한다면 form action + redirect
- 현재 화면에 validation error를 남겨야 한다면 action state
- 실패해도 쉽게 되돌릴 수 있고 빈번한 토글이라면 optimistic UI
- 외부 클라이언트도 같은 기능을 써야 한다면 route handler + shared command

---

## 흔한 실수

### 1) 클라이언트 검증을 서버 검증처럼 믿는다

`react-hook-form`, zod resolver, HTML required는 UX 장치다. 보안 장치가 아니다. Server Action에서도 같은 schema 또는 서버 전용 schema로 다시 검증해야 한다.

### 2) hidden input의 userId, role, tenantId를 그대로 저장한다

hidden input은 숨겨졌을 뿐 신뢰할 수 있는 값이 아니다. userId는 session에서, role과 tenant 접근 권한은 DB에서 확정해야 한다.

### 3) 권한 검증과 변경 사이에 race condition을 둔다

권한과 대상 상태를 transaction 밖에서 확인한 뒤 transaction 안에서 변경하면 그 사이 상태가 바뀔 수 있다. 중요한 상태 전이는 transaction 내부에서 다시 확인하거나 조건부 update를 사용해야 한다.

### 4) idempotency 없이 생성 요청을 처리한다

버튼 비활성화만으로는 중복 생성이 막히지 않는다. 주문, 결제, 초대, job 생성처럼 중복이 비용을 만드는 기능은 서버에서 key와 unique constraint로 막아야 한다.

### 5) transaction 안에서 느린 외부 API를 호출한다

메일, Slack, 결제 provider, 검색 색인 API를 transaction 내부에서 기다리면 lock 시간이 길어지고 재시도 의미가 꼬인다. outbox 또는 transaction 밖 후속 처리로 분리한다.

### 6) `revalidatePath("/")`로 모든 것을 해결한다

초기에는 편하지만 규모가 커지면 불필요한 재검증이 늘어난다. 변경된 read model에 맞춰 tag를 설계하고 좁게 무효화하는 편이 좋다.

### 7) `redirect()` 뒤에 중요한 코드를 둔다

`redirect()` 이후에는 후속 코드가 실행되지 않는다고 생각해야 한다. 감사 로그, outbox, revalidation은 redirect 전에 끝내야 한다.

### 8) 예상 가능한 도메인 에러와 시스템 장애를 같은 메시지로 뭉갠다

"저장 실패" 하나로 처리하면 사용자는 무엇을 고쳐야 할지 모른다. validation error, permission error, conflict, not found, transient failure를 구분해야 한다.

### 9) action 파일이 거대한 도메인 서비스가 된다

처음에는 편하지만 화면이 늘면 action마다 규칙이 복제된다. action은 입력과 UI 흐름 adapter로 두고, 핵심 변경 규칙은 command/service로 분리하는 편이 좋다.

### 10) 관측성 없이 action 실패를 삼킨다

사용자에게는 부드러운 메시지를 주더라도 서버에는 action name, user id, tenant id, target id, error code를 남겨야 한다. 그래야 "가끔 저장이 안 된다"는 제보를 추적할 수 있다.

---

## 체크리스트

Server Action을 운영 코드로 올리기 전에 아래 질문을 확인하자.

- 이 action은 React UI 전용인가, 외부 API로도 필요할 수 있는가
- 클라이언트에서 받은 값 중 서버에서 다시 확정해야 할 값은 무엇인가
- schema validation과 도메인 불변식 검증이 분리되어 있는가
- 권한 검증은 대상 리소스와 같은 기준으로 수행되는가
- 중요한 상태 전이는 transaction 안에서 다시 확인되는가
- 중복 submit, retry, double click에 대한 idempotency 전략이 있는가
- DB 변경, audit log, outbox event의 transaction 경계가 명확한가
- transaction 안에서 느린 외부 API를 기다리지 않는가
- 변경 후 어떤 path 또는 tag를 재검증해야 하는지 명시되어 있는가
- `redirect()` 또는 success 반환 전에 필요한 후속 처리가 끝나는가
- validation error, conflict, permission error, system error가 다른 메시지와 code로 구분되는가
- 실패 로그에 action name, user id, tenant id, target id, request id가 남는가
- optimistic UI를 쓴다면 실패 복구 UX가 있는가
- 같은 도메인 변경을 Route Handler나 worker에서도 써야 한다면 shared command로 분리되어 있는가
- 테스트에서 validation 실패, 권한 실패, 중복 요청, conflict, revalidation 호출을 확인하는가

---

## 테스트 전략: action 자체보다 "쓰기 계약"을 검증한다

Server Actions는 framework 경계와 엮여 있어 단위 테스트가 어색할 때가 있다. 그래서 모든 action을 억지로 직접 호출하는 것보다 쓰기 계약을 나눠 테스트하는 편이 좋다.

첫째, schema parser는 순수 함수로 테스트한다.

- 빈 문자열이 거부되는가
- 숫자 coercion이 기대대로 동작하는가
- 허용하지 않는 enum이 막히는가
- 이메일, slug, 날짜가 정규화되는가

둘째, domain command는 DB transaction을 포함해 integration test로 검증한다.

- 권한 없는 사용자는 변경할 수 없는가
- 이미 멤버인 이메일은 초대가 막히는가
- 같은 idempotency key는 같은 결과를 반환하는가
- 동시에 두 요청이 들어와도 unique constraint가 중복 생성을 막는가
- audit log와 outbox가 같이 생성되는가

셋째, action adapter는 얇게 smoke test하거나 E2E에서 확인한다.

- form submit 후 field error가 표시되는가
- 성공 후 redirect 또는 toast가 동작하는가
- 목록이 재검증되어 새 데이터가 보이는가
- pending state에서 버튼이 비활성화되는가

테스트의 핵심은 action 함수의 줄 수를 커버하는 것이 아니다. "이 쓰기 요청이 실패, 재시도, 중복, 경쟁 상태에서도 우리가 약속한 결과로 수렴하는가"를 검증하는 것이다.

---

## 한줄정리

Next.js Server Actions는 API Route를 줄이는 문법이 아니라, 사용자 입력에서 시작한 쓰기 요청을 서버의 신뢰 경계로 가져오는 장치다. 실무에서는 action 안에 validation, authorization, idempotency, transaction, outbox, revalidation, redirect 순서를 명확히 세워야 중복 생성, 권한 우회, 캐시 불일치, 실패 복구 혼란을 줄일 수 있다.
