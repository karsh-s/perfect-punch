export const msalConfig = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID,
    authority: `https://${import.meta.env.VITE_AZURE_TENANT_SUBDOMAIN}.ciamlogin.com/`,
    redirectUri: import.meta.env.VITE_REDIRECT_URI || "http://localhost:5173",
    knownAuthorities: [`${import.meta.env.VITE_AZURE_TENANT_SUBDOMAIN}.ciamlogin.com`],
  },
  cache: { cacheLocation: "sessionStorage" },
};

export const loginRequest = { scopes: ["openid", "profile", "email"] };
