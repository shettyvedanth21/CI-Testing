/* eslint-disable @typescript-eslint/no-require-imports */

const { expect, test } = require("@playwright/test");

function base64Json(value) {
  return Buffer.from(JSON.stringify(value), "utf8").toString("base64");
}

async function fulfillJson(route, data, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(data),
  });
}

function buildMe({ availableFeatures = ["machines", "calendar", "rules", "settings"], premiumFeatureGrants = [] } = {}) {
  return {
    user: {
      id: "user-1",
      email: "org-admin@example.com",
      full_name: "Org Admin",
      role: "org_admin",
      tenant_id: "SH00000001",
      is_active: true,
      created_at: new Date().toISOString(),
      last_login_at: null,
    },
    tenant: {
      id: "SH00000001",
      name: "Factory Ops",
      slug: "factory-ops",
      is_active: true,
      created_at: new Date().toISOString(),
    },
    plant_ids: ["plant-1"],
    entitlements: {
      premium_feature_grants: premiumFeatureGrants,
      role_feature_matrix: {
        org_admin: [],
        plant_manager: [],
        operator: [],
        viewer: [],
      },
      baseline_features_by_role: {
        org_admin: ["machines", "calendar", "rules", "settings"],
        plant_manager: ["machines", "rules", "settings"],
        operator: ["machines", "rules"],
        viewer: ["machines"],
      },
      effective_features_by_role: {
        org_admin: availableFeatures,
        plant_manager: ["machines", "rules", "settings"],
        operator: ["machines", "rules"],
        viewer: ["machines"],
      },
      available_features: availableFeatures,
      entitlements_version: 1,
    },
  };
}

async function seedSession(page, me) {
  await page.addInitScript((snapshot) => {
    window.sessionStorage.setItem("factoryops_access_token", snapshot.accessToken);
    window.sessionStorage.setItem("factoryops_refresh_token", "refresh-token");
    window.sessionStorage.setItem("factoryops_selected_tenant", "SH00000001");
    window.sessionStorage.setItem("factoryops_me", JSON.stringify(snapshot.me));
  }, {
    accessToken: `header.${base64Json({ sub: "user-1", role: "org_admin", tenant_id: "SH00000001", plant_ids: ["plant-1"], permissions_version: 1, tenant_entitlements_version: 1, exp: Math.floor(Date.now() / 1000) + 3600 })}.signature`,
    me,
  });

  await page.route("**/backend/auth/api/v1/auth/me", async (route) => {
    await fulfillJson(route, me);
  });
}

test("premium modules stay hidden and blocked when the org lacks the entitlement", async ({ page }) => {
  const me = buildMe();
  await seedSession(page, me);

  await page.goto("/analytics");

  await expect(page.getByText("Feature not enabled")).toBeVisible();
  await expect(page.getByText("Analytics is not enabled for this organisation or role.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Analytics" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Reports" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Waste Analysis" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Factory Copilot" })).toHaveCount(0);
});

test("premium modules appear in navigation when the org has the entitlement", async ({ page }) => {
  const me = buildMe({
    availableFeatures: ["machines", "calendar", "rules", "settings", "analytics", "reports", "waste_analysis", "copilot"],
    premiumFeatureGrants: ["analytics", "reports", "waste_analysis", "copilot"],
  });
  await seedSession(page, me);

  await page.goto("/machines");

  await expect(page.getByRole("link", { name: "Analytics" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Reports" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Waste Analysis" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Factory Copilot" })).toBeVisible();
});
