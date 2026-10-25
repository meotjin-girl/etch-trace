<#-- Split layout from the Figma login frame: intro on the left, form card on the right. -->
<#macro registrationLayout bodyClass="" displayInfo=false displayMessage=true displayRequiredFields=false>
<!DOCTYPE html>
<html lang="${(locale.currentLanguageTag)!'ko'}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <title>${msg("loginTitle",(realm.displayName!''))}</title>
  <#if properties.styles?has_content>
    <#list properties.styles?split(' ') as style>
      <link href="${url.resourcesPath}/${style}" rel="stylesheet">
    </#list>
  </#if>
</head>
<body class="trace ${bodyClass}">
  <main class="trace-login">
    <section class="trace-intro" aria-label="TRACE 소개">
      <div class="trace-brand">
        <svg width="46" height="46" viewBox="0 0 34 34" aria-hidden="true">
          <rect x="7" y="7" width="20" height="20" transform="rotate(45 17 17)" fill="none" stroke="currentColor" stroke-width="2.2" />
        </svg>
        <strong>TRACE</strong>
      </div>
      <h1>식각 공정 이상을<br>근거와 함께 조사합니다.</h1>
      <p class="trace-flow">합성 알람 <span>→</span> AI 조사 <span>→</span> 엔지니어 판단 <span>→</span> 기록</p>
      <p class="trace-note">합성 데이터 · 실제 장비 데이터 아님</p>
    </section>
    <section class="trace-panel">
      <div class="trace-card">
        <h2><#nested "header"></h2>
        <#if displayMessage && message?has_content && (message.type != 'warning' || !isAppInitiatedAction??)>
          <p class="trace-alert trace-alert-${message.type}" role="alert">${kcSanitize(message.summary)?no_esc}</p>
        </#if>
        <#nested "form">
        <#nested "socialProviders">
        <#if displayInfo><div class="trace-info"><#nested "info"></div></#if>
      </div>
    </section>
  </main>
</body>
</html>
</#macro>
