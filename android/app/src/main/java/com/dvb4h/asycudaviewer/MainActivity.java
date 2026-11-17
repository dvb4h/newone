package com.dvb4h.asycudaviewer;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.DownloadManager;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.text.InputType;
import android.view.Gravity;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.SslErrorHandler;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebStorage;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.Toast;

/**
 * تطبيق بسيط يعرض بوابة أسيكودا (أو أي رابط ويب يحدده المستخدم) داخل WebView
 * مع دعم تسجيل الدخول (الكوكيز)، رفع الملفات، تنزيل الملفات، ووضع سطح المكتب.
 */
public class MainActivity extends Activity {

    private static final String PREFS = "settings";
    private static final String KEY_URL = "portal_url";
    private static final String KEY_DESKTOP = "desktop_mode";
    private static final int REQ_FILE = 1001;
    private static final int REQ_STORAGE = 1002;

    private static final String DESKTOP_UA =
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    + "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";

    private WebView webView;
    private ProgressBar progressBar;
    private SharedPreferences prefs;
    private String defaultUserAgent;
    private ValueCallback<Uri[]> filePathCallback;
    private PendingDownload pendingDownload;

    private static class PendingDownload {
        String url, userAgent, contentDisposition, mimeType;
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);

        FrameLayout root = new FrameLayout(this);
        webView = new WebView(this);
        root.addView(webView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        FrameLayout.LayoutParams pbParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(4));
        pbParams.gravity = Gravity.TOP;
        root.addView(progressBar, pbParams);
        setContentView(root);

        setupWebView();

        if (savedInstanceState != null) {
            webView.restoreState(savedInstanceState);
        } else {
            String url = prefs.getString(KEY_URL, null);
            if (url == null || url.isEmpty()) {
                showUrlDialog(true);
            } else {
                webView.loadUrl(url);
            }
        }
    }

    private void setupWebView() {
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setBuiltInZoomControls(true);
        s.setDisplayZoomControls(false);
        s.setSupportZoom(true);
        s.setAllowFileAccess(false);
        s.setJavaScriptCanOpenWindowsAutomatically(true);
        s.setSupportMultipleWindows(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        defaultUserAgent = s.getUserAgentString();
        applyDesktopMode(prefs.getBoolean(KEY_DESKTOP, false), false);

        CookieManager cm = CookieManager.getInstance();
        cm.setAcceptCookie(true);
        cm.setAcceptThirdPartyCookies(webView, true);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase();
                if (scheme.equals("http") || scheme.equals("https")) {
                    return false; // يفتح داخل التطبيق
                }
                // روابط مثل tel: أو mailto: تفتح في التطبيق المناسب
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                } catch (ActivityNotFoundException e) {
                    toast("لا يوجد تطبيق لفتح هذا الرابط");
                }
                return true;
            }

            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                progressBar.setVisibility(View.VISIBLE);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                progressBar.setVisibility(View.GONE);
                CookieManager.getInstance().flush();
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request,
                                        WebResourceError error) {
                if (request.isForMainFrame()) {
                    showErrorPage(String.valueOf(error.getDescription()));
                }
            }

            @Override
            public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                // بعض البوابات الحكومية تستخدم شهادات غير موثقة؛ نسأل المستخدم بدل الرفض الصامت
                new AlertDialog.Builder(MainActivity.this)
                        .setTitle("تحذير أمني")
                        .setMessage("شهادة الأمان (SSL) لهذا الموقع غير موثوقة:\n"
                                + error.getUrl()
                                + "\n\nتابع فقط إذا كنت متأكداً أن هذا هو الموقع الصحيح.")
                        .setPositiveButton("متابعة", (d, w) -> handler.proceed())
                        .setNegativeButton("إلغاء", (d, w) -> handler.cancel())
                        .setOnCancelListener(d -> handler.cancel())
                        .show();
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
                progressBar.setVisibility(newProgress < 100 ? View.VISIBLE : View.GONE);
            }

            @Override
            public void onReceivedTitle(WebView view, String title) {
                if (title != null && !title.isEmpty() && !title.startsWith("http")) {
                    setTitle(title);
                }
            }

            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback,
                                             FileChooserParams params) {
                if (filePathCallback != null) {
                    filePathCallback.onReceiveValue(null);
                }
                filePathCallback = callback;
                Intent intent = params.createIntent();
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                if (params.getMode() == FileChooserParams.MODE_OPEN_MULTIPLE) {
                    intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
                }
                try {
                    startActivityForResult(Intent.createChooser(intent, "اختر ملفاً"), REQ_FILE);
                } catch (ActivityNotFoundException e) {
                    filePathCallback = null;
                    toast("لا يوجد تطبيق لاختيار الملفات");
                    return false;
                }
                return true;
            }
        });

        webView.setDownloadListener((url, userAgent, contentDisposition, mimeType, length) -> {
            PendingDownload p = new PendingDownload();
            p.url = url;
            p.userAgent = userAgent;
            p.contentDisposition = contentDisposition;
            p.mimeType = mimeType;
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q
                    && checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE)
                    != PackageManager.PERMISSION_GRANTED) {
                pendingDownload = p;
                requestPermissions(new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE},
                        REQ_STORAGE);
            } else {
                startDownload(p);
            }
        });
    }

    private void startDownload(PendingDownload p) {
        if (p.url.startsWith("blob:") || p.url.startsWith("data:")) {
            toast("هذا النوع من التنزيل غير مدعوم، جرّب «فتح في المتصفح»");
            return;
        }
        try {
            String fileName = URLUtil.guessFileName(p.url, p.contentDisposition, p.mimeType);
            DownloadManager.Request req = new DownloadManager.Request(Uri.parse(p.url));
            req.setMimeType(p.mimeType);
            String cookies = CookieManager.getInstance().getCookie(p.url);
            if (cookies != null) req.addRequestHeader("Cookie", cookies);
            req.addRequestHeader("User-Agent", p.userAgent);
            req.setTitle(fileName);
            req.setNotificationVisibility(
                    DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            req.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, fileName);
            DownloadManager dm = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
            dm.enqueue(req);
            toast("جارِ تنزيل: " + fileName);
        } catch (Exception e) {
            toast("تعذّر التنزيل: " + e.getMessage());
        }
    }

    private void applyDesktopMode(boolean desktop, boolean reload) {
        WebSettings s = webView.getSettings();
        s.setUserAgentString(desktop ? DESKTOP_UA : defaultUserAgent);
        prefs.edit().putBoolean(KEY_DESKTOP, desktop).apply();
        if (reload) webView.reload();
    }

    private void showUrlDialog(boolean firstTime) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(20), dp(8), dp(20), 0);
        final EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        input.setHint("https://...");
        input.setTextDirection(View.TEXT_DIRECTION_LTR);
        String current = prefs.getString(KEY_URL, "");
        input.setText(current);
        box.addView(input);

        AlertDialog.Builder b = new AlertDialog.Builder(this)
                .setTitle("رابط بوابة أسيكودا")
                .setMessage("أدخل رابط بوابة أسيكودا (نفس الرابط الذي تفتحه في المتصفح):")
                .setView(box)
                .setPositiveButton("حفظ وفتح", (d, w) -> {
                    String url = normalizeUrl(input.getText().toString());
                    if (url == null) {
                        toast("الرابط غير صحيح");
                        showUrlDialog(firstTime);
                        return;
                    }
                    prefs.edit().putString(KEY_URL, url).apply();
                    webView.loadUrl(url);
                });
        if (firstTime) {
            b.setCancelable(false);
        } else {
            b.setNegativeButton("إلغاء", null);
        }
        b.show();
    }

    private static String normalizeUrl(String raw) {
        if (raw == null) return null;
        String url = raw.trim();
        if (url.isEmpty()) return null;
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "https://" + url;
        }
        return URLUtil.isValidUrl(url) ? url : null;
    }

    private void showErrorPage(String description) {
        String html = "<html dir='rtl'><head><meta name='viewport' content='width=device-width'>"
                + "<style>body{font-family:sans-serif;text-align:center;padding:40px 20px;color:#333}"
                + "h2{color:#C8102E}button{font-size:18px;padding:10px 30px;margin-top:20px;"
                + "background:#0B5D3B;color:#fff;border:0;border-radius:8px}</style></head><body>"
                + "<h2>تعذّر فتح البوابة</h2>"
                + "<p>تأكد من اتصالك بالإنترنت أو من صحة الرابط.</p>"
                + "<p style='color:#888;font-size:13px' dir='ltr'>" + escape(description) + "</p>"
                + "<button onclick='history.back()'>إعادة المحاولة</button>"
                + "</body></html>";
        webView.loadDataWithBaseURL(null, html, "text/html", "UTF-8", null);
    }

    private static String escape(String s) {
        return s == null ? "" : s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        getMenuInflater().inflate(R.menu.main_menu, menu);
        menu.findItem(R.id.action_desktop).setChecked(prefs.getBoolean(KEY_DESKTOP, false));
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        int id = item.getItemId();
        String home = prefs.getString(KEY_URL, null);
        if (id == R.id.action_reload) {
            String current = webView.getUrl();
            if (current == null || current.startsWith("data:") || current.equals("about:blank")) {
                if (home != null) webView.loadUrl(home);
            } else {
                webView.reload();
            }
            return true;
        } else if (id == R.id.action_home) {
            if (home != null) webView.loadUrl(home);
            return true;
        } else if (id == R.id.action_desktop) {
            boolean desktop = !item.isChecked();
            item.setChecked(desktop);
            applyDesktopMode(desktop, true);
            return true;
        } else if (id == R.id.action_change_url) {
            showUrlDialog(false);
            return true;
        } else if (id == R.id.action_open_browser) {
            String current = webView.getUrl();
            String target = (current != null && current.startsWith("http")) ? current : home;
            if (target != null) {
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(target)));
                } catch (ActivityNotFoundException e) {
                    toast("لا يوجد متصفح");
                }
            }
            return true;
        } else if (id == R.id.action_clear) {
            new AlertDialog.Builder(this)
                    .setMessage("سيتم تسجيل خروجك ومسح الكاش. متابعة؟")
                    .setPositiveButton("نعم", (d, w) -> {
                        CookieManager.getInstance().removeAllCookies(null);
                        CookieManager.getInstance().flush();
                        WebStorage.getInstance().deleteAllData();
                        webView.clearCache(true);
                        webView.clearHistory();
                        if (home != null) webView.loadUrl(home);
                    })
                    .setNegativeButton("لا", null)
                    .show();
            return true;
        }
        return super.onOptionsItemSelected(item);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == REQ_FILE) {
            if (filePathCallback != null) {
                filePathCallback.onReceiveValue(
                        WebChromeClient.FileChooserParams.parseResult(resultCode, data));
                filePathCallback = null;
            }
            return;
        }
        super.onActivityResult(requestCode, resultCode, data);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions,
                                           int[] grantResults) {
        if (requestCode == REQ_STORAGE) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED
                    && pendingDownload != null) {
                startDownload(pendingDownload);
            } else {
                toast("يلزم إذن التخزين لتنزيل الملفات");
            }
            pendingDownload = null;
            return;
        }
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        webView.saveState(outState);
    }

    @Override
    protected void onPause() {
        super.onPause();
        webView.onPause();
        CookieManager.getInstance().flush();
    }

    @Override
    protected void onResume() {
        super.onResume();
        webView.onResume();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.destroy();
        }
        super.onDestroy();
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    private void toast(String msg) {
        Toast.makeText(this, msg, Toast.LENGTH_LONG).show();
    }
}
