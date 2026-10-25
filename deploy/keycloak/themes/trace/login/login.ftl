<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('username','password'); section>
  <#if section = "header">
    TRACE에 로그인
  <#elseif section = "form">
    <p class="trace-sub">근무자 계정으로 조사 화면을 확인합니다.</p>
    <form id="kc-form-login" action="${url.loginAction}" method="post" onsubmit="login.disabled = true; return true;">
      <label class="trace-field" for="username">
        <span>계정</span>
        <input id="username" name="username" type="text" value="${(login.username!'')}" placeholder="사용자 ID"
          autocomplete="username" autofocus
          aria-invalid="<#if messagesPerField.existsError('username','password')>true</#if>">
      </label>
      <label class="trace-field" for="password">
        <span>비밀번호</span>
        <input id="password" name="password" type="password" placeholder="••••••••" autocomplete="current-password"
          aria-invalid="<#if messagesPerField.existsError('username','password')>true</#if>">
      </label>
      <#if messagesPerField.existsError('username','password')>
        <p class="trace-alert trace-alert-error" role="alert">${kcSanitize(messagesPerField.getFirstError('username','password'))?no_esc}</p>
      </#if>
      <input type="hidden" id="id-hidden-input" name="credentialId" <#if auth.selectedCredential?has_content>value="${auth.selectedCredential}"</#if>>
      <button class="trace-button" name="login" id="kc-login" type="submit">로그인</button>
    </form>
    <p class="trace-foot">Keycloak 계정 인증</p>
  </#if>
</@layout.registrationLayout>
