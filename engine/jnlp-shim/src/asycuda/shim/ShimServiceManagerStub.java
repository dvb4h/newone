package asycuda.shim;

import java.net.MalformedURLException;
import java.net.URL;
import javax.jnlp.BasicService;
import javax.jnlp.ServiceManagerStub;
import javax.jnlp.UnavailableServiceException;

/**
 * يوفّر BasicService بالاعتماد على الخاصية jnlp.codebase (تُمرَّر من سكربت التشغيل).
 */
public class ShimServiceManagerStub implements ServiceManagerStub {
    private static final String BASIC = "javax.jnlp.BasicService";

    private final BasicService basic = new BasicService() {
        public URL getCodeBase() {
            try {
                return new URL(System.getProperty("jnlp.codebase", "https://asy.mof.gov.iq/aw/"));
            } catch (MalformedURLException e) {
                return null;
            }
        }
        public boolean isOffline() { return false; }
        public boolean showDocument(URL url) {
            System.err.println("[jnlp-shim] showDocument: " + url);
            return false;
        }
        public boolean isWebBrowserSupported() { return false; }
    };

    public Object lookup(String name) throws UnavailableServiceException {
        if (BASIC.equals(name)) return basic;
        System.err.println("[jnlp-shim] service not available: " + name);
        throw new UnavailableServiceException(name);
    }

    public String[] getServiceNames() { return new String[]{BASIC}; }
}
