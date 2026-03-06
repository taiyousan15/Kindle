import { test, expect } from "@playwright/test";

test.describe("ホームページ", () => {
  test("ページが表示される", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Kindle/i);
  });

  test("ナビゲーションにキーワードリンクが存在する", async ({ page }) => {
    await page.goto("/");
    const nav = page.locator("nav, aside");
    await expect(nav).toBeVisible();
  });
});

test.describe("売上予測ページ", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/prediction");
  });

  test("ページタイトルが表示される", async ({ page }) => {
    await expect(page.getByText("売上予測シミュレーター")).toBeVisible();
  });

  test("BSR入力フィールドが存在する", async ({ page }) => {
    const input = page.locator("input[type='number']");
    await expect(input).toBeVisible();
    await expect(input).toHaveValue("5000");
  });

  test("ジャンル選択プルダウンが存在する", async ({ page }) => {
    const select = page.locator("select");
    await expect(select).toBeVisible();
    await expect(select).toHaveValue("ビジネス・経済");
  });

  test("計算ボタンをクリックすると結果が表示される", async ({ page }) => {
    await page.route("**/api/v1/prediction/bsr-to-sales**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          bsr: 5000,
          genre: "ビジネス・経済",
          daily_estimated: 2.5,
          monthly_estimated: 75,
          lower_bound: 60,
          upper_bound: 90,
          error_range_pct: 20,
          note: "テスト用推定値",
        }),
      })
    );

    await page.getByRole("button", { name: /推定販売数を計算/ }).click();
    await expect(page.getByText("BSR 5,000 の推定結果")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("75冊")).toBeVisible();
  });

  test("APIエラー時にクライアントサイド計算にフォールバックする", async ({ page }) => {
    await page.route("**/api/v1/prediction/bsr-to-sales**", (route) =>
      route.abort("failed")
    );

    await page.getByRole("button", { name: /推定販売数を計算/ }).click();
    // フォールバック計算が実行され、結果が表示される
    await expect(page.getByText(/推定結果/)).toBeVisible({ timeout: 5000 });
  });

  test("BSR参考値グラフが結果と共に表示される", async ({ page }) => {
    await page.route("**/api/v1/prediction/bsr-to-sales**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          bsr: 5000,
          genre: "ビジネス・経済",
          daily_estimated: 2.5,
          monthly_estimated: 75,
          lower_bound: 60,
          upper_bound: 90,
          error_range_pct: 20,
          note: "テスト用推定値",
        }),
      })
    );

    await page.getByRole("button", { name: /推定販売数を計算/ }).click();
    await expect(page.getByText("BSR参考値グラフ")).toBeVisible({ timeout: 5000 });
  });
});

test.describe("キーワードページ", () => {
  test("ページが表示される", async ({ page }) => {
    await page.goto("/keywords");
    await expect(page.getByRole("heading")).toBeVisible();
  });
});

test.describe("ジャンルページ", () => {
  test("ページが表示される", async ({ page }) => {
    await page.goto("/genres");
    await expect(page.getByRole("heading")).toBeVisible();
  });
});
