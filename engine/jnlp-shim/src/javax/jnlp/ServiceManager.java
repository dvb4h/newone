package javax.jnlp;

/**
 * بديل مفتوح المصدر لـ ServiceManager الخاص بـ Java Web Start.
 * يوفّر BasicService فقط، وباقي الخدمات تُعتبر غير متوفرة (كما يسمح المعيار).
 */
public final class ServiceManager {
    private static ServiceManagerStub stub;

    private ServiceManager() { }

    public static synchronized Object lookup(String name) throws UnavailableServiceException {
        if (stub == null) stub = new asycuda.shim.ShimServiceManagerStub();
        return stub.lookup(name);
    }

    public static synchronized String[] getServiceNames() {
        if (stub == null) stub = new asycuda.shim.ShimServiceManagerStub();
        return stub.getServiceNames();
    }

    public static synchronized void setServiceManagerStub(ServiceManagerStub s) {
        if (stub == null) stub = s;
    }
}
