# Frontend TDD Best Practices Guide

## 개요

백엔드는 TDD로 구현이 용이하지만, 프론트엔드 TDD는 UI 구성을 어떻게 전달하고 테스트할지에 대한 고민이 필요합니다. 특히 로직/validation은 TDD가 적합하지만, UI 레이아웃이나 인터랙션을 AI Agent에게 전달하는 것은 다른 접근이 필요합니다.

---

## 🎨 UI 사양 전달 Best Practices

### 1. 시각적 문서 + 행동 정의 (추천)

가장 효과적인 방법은 **시각적 자료**와 **행동 정의**를 결합하는 것입니다.

#### 예시 구조:

```markdown
# LoginForm Component Specification

## Visual Layout
![Login Form Mockup](./mockups/login-form.png)

## Behavior Specifications (BDD Style)
- GIVEN 사용자가 로그인 페이지에 있을 때
- WHEN 이메일 입력란에 유효하지 않은 이메일을 입력하면
- THEN "유효한 이메일 주소를 입력해주세요" 에러 메시지가 표시된다

## Component Requirements
- Email input (type=email, required)
- Password input (type=password, required)
- Submit button (disabled when form is invalid)
- Error message container (hidden by default)
```

#### 사용 도구:
- **Figma**: 디자인을 이미지로 export
- **Excalidraw**: 간단한 와이어프레임
- **AI Image Generation**: UI 목업 생성
- **손그림 스캔**: 빠른 프로토타이핑

---

### 2. Component-Driven Development (CDD) with Storybook

UI 컴포넌트를 독립적으로 개발하고 문서화하는 방식입니다.

#### Storybook 예시:

```javascript
// Button.stories.js
export default {
  title: 'Components/Button',
  component: Button,
};

export const Primary = {
  args: {
    label: 'Click me',
    variant: 'primary',
    onClick: () => alert('Clicked!'),
  },
};

export const Disabled = {
  args: {
    label: 'Disabled',
    disabled: true,
  },
};

export const Loading = {
  args: {
    label: 'Loading...',
    isLoading: true,
  },
};
```

#### 장점:
- AI Agent가 Storybook 파일을 보고 정확한 UI 상태 이해
- 시각적으로 확인 가능
- 자동으로 문서화됨
- 다양한 상태를 독립적으로 테스트 가능

---

### 3. Testing Library + Accessibility-First TDD

UI를 **사용자 관점**에서 테스트 작성하는 방식입니다.

#### 테스트 예시:

```javascript
// LoginForm.test.jsx
import { render, screen, userEvent } from '@testing-library/react';
import { LoginForm } from './LoginForm';

describe('LoginForm', () => {
  it('shows error when invalid email is entered', async () => {
    render(<LoginForm />);
    
    const emailInput = screen.getByLabelText(/email/i);
    const submitButton = screen.getByRole('button', { name: /로그인/i });
    
    await userEvent.type(emailInput, 'invalid-email');
    await userEvent.click(submitButton);
    
    expect(screen.getByText(/유효한 이메일/i)).toBeInTheDocument();
  });

  it('enables submit button when form is valid', async () => {
    render(<LoginForm />);
    
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /로그인/i });
    
    expect(submitButton).toBeDisabled();
    
    await userEvent.type(emailInput, 'user@example.com');
    await userEvent.type(passwordInput, 'password123');
    
    expect(submitButton).toBeEnabled();
  });
});
```

#### AI Agent에게 전달할 정보:

```markdown
## Test Requirements
- 이메일 입력란은 "이메일" 레이블을 가진 input이어야 함
- 제출 버튼은 "로그인" 텍스트를 포함해야 함
- 유효하지 않은 이메일 입력 시 "유효한 이메일 주소를 입력해주세요" 메시지 표시
- 폼이 유효하지 않을 때 제출 버튼은 비활성화 상태
```

---

### 4. Visual Regression Testing

UI 변경사항을 자동으로 감지하는 방식입니다.

#### Playwright with Screenshots:

```javascript
// login.spec.js
import { test, expect } from '@playwright/test';

test('login form matches design', async ({ page }) => {
  await page.goto('/login');
  await expect(page).toHaveScreenshot('login-form.png');
});

test('login form shows error state', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[type="email"]', 'invalid-email');
  await page.click('button[type="submit"]');
  await expect(page).toHaveScreenshot('login-form-error.png');
});
```

#### 도구 옵션:
- **Playwright**: 스크린샷 비교 내장
- **Chromatic**: Storybook과 연동하여 시각적 회귀 테스팅
- **Percy**: 스냅샷 비교 서비스
- **BackstopJS**: 오픈소스 시각적 회귀 테스팅

---

### 5. 행동 중심 사양 (BDD Format)

Gherkin 스타일로 명확하게 정의하는 방식입니다.

#### 예시:

```gherkin
Feature: 데이터 동기화 UI
  
  Scenario: 동기화 시작 버튼 클릭
    Given 사용자가 테이블 목록 페이지에 있고
    And "EMPLOYEES" 테이블이 선택되어 있을 때
    When 사용자가 "동기화 시작" 버튼을 클릭하면
    Then 진행률 바가 표시되고
    And 버튼이 "동기화 중..." 텍스트로 변경되며
    And 버튼이 비활성화된다
  
  Scenario: 동기화 완료
    Given 동기화가 진행 중일 때
    When 동기화가 성공적으로 완료되면
    Then 버튼이 "완료" 텍스트로 변경되고
    And 버튼이 초록색으로 표시되며
    And 2초 후 원래 상태로 돌아간다
  
  Scenario: 동기화 실패
    Given 동기화가 진행 중일 때
    When 동기화가 실패하면
    Then 에러 메시지가 표시되고
    And 버튼이 "재시도" 텍스트로 변경되며
    And 버튼이 빨간색으로 표시된다
```

#### 도구:
- **Cucumber**: JavaScript/TypeScript 지원
- **Playwright Test**: BDD 스타일 지원
- **Jest-Cucumber**: Jest와 통합

---

## 🛠️ 추천 워크플로우

### Phase 1: 사양 작성

1. **와이어프레임 생성**
   - Figma, Excalidraw, 또는 손그림
   - 주요 화면과 상태별 UI 정의

2. **행동 사양 작성**
   - BDD format으로 사용자 시나리오 작성
   - 각 인터랙션의 기대 결과 명시

3. **접근성 요구사항 정의**
   - 버튼 레이블, ARIA 속성
   - 키보드 네비게이션
   - 스크린 리더 지원

### Phase 2: TDD 구현

1. **테스트 먼저 작성** (Testing Library)
   ```javascript
   // 실패하는 테스트
   test('sync button shows progress when clicked', async () => {
     render(<SyncButton tableId="EMPLOYEES" />);
     const button = screen.getByRole('button', { name: /동기화 시작/i });
     
     await userEvent.click(button);
     
     expect(screen.getByText(/동기화 중/i)).toBeInTheDocument();
     expect(button).toBeDisabled();
   });
   ```

2. **최소 구현** (테스트 통과)
   ```javascript
   function SyncButton({ tableId }) {
     const [syncing, setSyncing] = useState(false);
     
     const handleClick = () => {
       setSyncing(true);
       // TODO: 실제 동기화 로직
     };
     
     return (
       <button onClick={handleClick} disabled={syncing}>
         {syncing ? '동기화 중...' : '동기화 시작'}
       </button>
     );
   }
   ```

3. **리팩토링** (스타일 개선, 로직 분리)

### Phase 3: 시각적 검증

1. **Storybook으로 시각적 확인**
   - 다양한 상태 확인
   - 인터랙션 테스트

2. **스크린샷 테스트** (선택사항)
   - 자동화된 시각적 회귀 테스팅

3. **수동 리뷰**
   - AI Agent에게 스크린샷 전달하여 피드백 요청
   - 디자인 시스템 일관성 확인

---

## 💡 AI Agent와 협업 시 팁

### 효과적인 프롬프트 구조:

```markdown
# UI 구현 요청

## 목업 이미지
[이미지 첨부 또는 상세 설명]

## 레이아웃
- 헤더: 좌측에 로고, 우측에 사용자 메뉴
- 메인: 좌측 사이드바 (테이블 목록), 우측 컨텐츠 영역
- 푸터: 저작권 정보

## 컴포넌트 상세

### SyncButton
**기본 상태:**
- 파란색 배경 (#3B82F6)
- "동기화 시작" 텍스트
- 호버 시 약간 어두워짐

**클릭 시 (로딩 상태):**
- 회색 배경 (#9CA3AF)
- "동기화 중..." 텍스트
- 스피너 아이콘 (좌측)
- 비활성화 상태

**완료 시:**
- 초록색 배경 (#10B981)
- "완료" 텍스트
- 체크 아이콘
- 2초간 유지 후 원래 상태로 복귀

**에러 시:**
- 빨간색 배경 (#EF4444)
- "재시도" 텍스트
- 경고 아이콘

## 테스트 시나리오
1. 버튼이 기본 상태로 렌더링된다
2. 클릭 시 로딩 상태로 변경된다
3. 동기화 완료 시 성공 메시지가 표시된다
4. 에러 발생 시 에러 메시지가 표시된다
5. 재시도 버튼 클릭 시 다시 동기화가 시작된다

## 접근성 요구사항
- 버튼은 명확한 레이블을 가져야 함
- 로딩 중일 때 aria-busy="true" 설정
- 키보드로 접근 가능 (Tab, Enter)
- 포커스 상태 시각적 표시
```

### 단계별 협업 방식:

1. **사양 공유**
   - 위와 같은 상세 문서 제공
   - 와이어프레임 이미지 첨부

2. **테스트 작성 요청**
   ```
   "위 사양을 기반으로 Testing Library를 사용한 테스트를 작성해주세요."
   ```

3. **구현 요청**
   ```
   "작성된 테스트를 통과하는 최소 구현을 해주세요."
   ```

4. **스타일링 요청**
   ```
   "기능은 동작하니 이제 디자인 사양에 맞게 스타일을 적용해주세요."
   ```

5. **리뷰 및 개선**
   ```
   "접근성 측면에서 개선할 점이 있는지 확인해주세요."
   ```

---

## 📚 프레임워크/도구 조합 추천

### 최소 구성 (시작하기 좋음)

**도구:**
- **Testing Library** (UI 테스팅)
- **Vitest** 또는 **Jest** (테스트 러너)
- **Markdown 사양 문서** (AI Agent 전달용)

**장점:**
- 빠른 시작
- 학습 곡선 낮음
- 핵심 TDD 워크플로우 지원

**예시 설정:**
```json
{
  "devDependencies": {
    "@testing-library/react": "^14.0.0",
    "@testing-library/user-event": "^14.0.0",
    "vitest": "^1.0.0",
    "@vitejs/plugin-react": "^4.0.0"
  }
}
```

---

### 중급 구성 (프로덕션 권장)

**도구:**
- 위 최소 구성 +
- **Storybook** (컴포넌트 개발/문서화)
- **Playwright** (E2E 테스팅)

**장점:**
- 컴포넌트 독립 개발
- 시각적 문서화
- 통합 테스트 지원

**추가 설정:**
```json
{
  "devDependencies": {
    "@storybook/react-vite": "^7.0.0",
    "@playwright/test": "^1.40.0"
  }
}
```

**Storybook 설정:**
```bash
npx storybook@latest init
```

---

### 고급 구성 (대규모 프로젝트)

**도구:**
- 위 중급 구성 +
- **Chromatic** (시각적 회귀 테스팅)
- **Figma** (디자인 시스템 연동)
- **MSW** (Mock Service Worker - API 모킹)

**장점:**
- 자동화된 시각적 QA
- 디자인-개발 일관성
- 완전한 격리 테스트

**추가 설정:**
```json
{
  "devDependencies": {
    "chromatic": "^10.0.0",
    "msw": "^2.0.0",
    "figma-api": "^1.11.0"
  }
}
```

---

## 🎯 실전 적용 예시: Oracle-DuckDB Sync UI

### 1. 테이블 목록 컴포넌트

#### 사양 문서:

```markdown
# TableList Component

## Layout
- 좌측 사이드바 (300px 고정 너비)
- 테이블 목록 (스크롤 가능)
- 각 테이블 항목: 이름, 행 수, 동기화 상태

## States
- 로딩: 스켈레톤 UI 표시
- 빈 목록: "테이블이 없습니다" 메시지
- 에러: 에러 메시지 + 재시도 버튼
- 정상: 테이블 목록 표시

## Interactions
- 테이블 클릭 → 상세 정보 표시
- 호버 → 배경색 변경
- 선택된 테이블 → 하이라이트
```

#### 테스트:

```javascript
// TableList.test.jsx
describe('TableList', () => {
  it('shows loading skeleton initially', () => {
    render(<TableList />);
    expect(screen.getByTestId('skeleton-loader')).toBeInTheDocument();
  });

  it('displays tables when loaded', async () => {
    const tables = [
      { name: 'EMPLOYEES', rowCount: 1000, status: 'synced' },
      { name: 'DEPARTMENTS', rowCount: 50, status: 'pending' }
    ];
    
    render(<TableList tables={tables} />);
    
    expect(screen.getByText('EMPLOYEES')).toBeInTheDocument();
    expect(screen.getByText('1000 rows')).toBeInTheDocument();
  });

  it('highlights selected table', async () => {
    const tables = [{ name: 'EMPLOYEES', rowCount: 1000 }];
    const onSelect = jest.fn();
    
    render(<TableList tables={tables} onSelect={onSelect} />);
    
    const tableItem = screen.getByText('EMPLOYEES');
    await userEvent.click(tableItem);
    
    expect(onSelect).toHaveBeenCalledWith('EMPLOYEES');
    expect(tableItem.closest('li')).toHaveClass('selected');
  });
});
```

---

### 2. 동기화 진행률 컴포넌트

#### 사양 문서:

```markdown
# SyncProgress Component

## Visual
- 진행률 바 (0-100%)
- 현재/전체 행 수 표시
- 예상 남은 시간
- 일시정지/재개 버튼

## States
- idle: 진행률 바 숨김
- syncing: 진행률 바 표시, 애니메이션
- paused: 진행률 바 표시, 애니메이션 정지
- completed: 100%, 초록색
- error: 빨간색, 에러 메시지
```

#### 테스트:

```javascript
// SyncProgress.test.jsx
describe('SyncProgress', () => {
  it('shows progress percentage', () => {
    render(<SyncProgress current={500} total={1000} />);
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('displays row counts', () => {
    render(<SyncProgress current={500} total={1000} />);
    expect(screen.getByText('500 / 1,000 rows')).toBeInTheDocument();
  });

  it('allows pausing sync', async () => {
    const onPause = jest.fn();
    render(<SyncProgress status="syncing" onPause={onPause} />);
    
    const pauseButton = screen.getByRole('button', { name: /일시정지/i });
    await userEvent.click(pauseButton);
    
    expect(onPause).toHaveBeenCalled();
  });
});
```

---

## 📋 체크리스트

### 사양 작성 단계
- [ ] 와이어프레임 또는 목업 준비
- [ ] 주요 사용자 시나리오 BDD 형식으로 작성
- [ ] 컴포넌트별 상태 정의 (기본, 로딩, 에러, 성공 등)
- [ ] 접근성 요구사항 명시
- [ ] 인터랙션 상세 설명 (클릭, 호버, 포커스 등)

### 테스트 작성 단계
- [ ] 렌더링 테스트 (기본 상태)
- [ ] 사용자 인터랙션 테스트
- [ ] 상태 변경 테스트
- [ ] 에러 처리 테스트
- [ ] 접근성 테스트 (ARIA, 키보드 네비게이션)

### 구현 단계
- [ ] 테스트 통과하는 최소 구현
- [ ] 스타일 적용
- [ ] 애니메이션/트랜지션 추가
- [ ] 반응형 디자인 적용
- [ ] 성능 최적화 (필요시)

### 검증 단계
- [ ] 모든 테스트 통과
- [ ] Storybook에서 시각적 확인
- [ ] 브라우저에서 수동 테스트
- [ ] 접근성 검증 (axe, Lighthouse)
- [ ] 크로스 브라우저 테스트 (필요시)

---

## 🔑 핵심 원칙

1. **사용자 관점으로 테스트**
   - 구현 세부사항이 아닌 사용자 행동 테스트
   - Testing Library의 철학 따르기

2. **명확한 사양 문서**
   - 시각적 자료 + 텍스트 설명
   - 모호함 없이 구체적으로

3. **점진적 개선**
   - 최소 구현 → 스타일 → 최적화
   - 한 번에 모든 것을 하지 않기

4. **자동화 우선**
   - 반복 가능한 테스트
   - CI/CD 통합

5. **접근성 필수**
   - 처음부터 고려
   - 나중에 추가하기 어려움

---

## 📖 참고 자료

### 공식 문서
- [Testing Library](https://testing-library.com/)
- [Storybook](https://storybook.js.org/)
- [Playwright](https://playwright.dev/)
- [Vitest](https://vitest.dev/)

### 학습 자료
- [Kent C. Dodds - Testing JavaScript](https://testingjavascript.com/)
- [Component-Driven Development](https://www.componentdriven.org/)
- [Web Accessibility Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

### 예제 프로젝트
- [Real World App](https://github.com/gothinkster/realworld)
- [Storybook Examples](https://storybook.js.org/showcase)

---

## 결론

프론트엔드 TDD는 백엔드와 다른 접근이 필요하지만, 올바른 도구와 워크플로우를 사용하면 매우 효과적입니다.

**핵심은:**
1. 명확한 시각적 사양
2. 사용자 관점의 테스트
3. 점진적 구현

이 가이드를 따라 프로젝트에 맞는 방식을 선택하고 적용해보세요!
