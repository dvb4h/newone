package javax.jnlp;
public interface IntegrationService {
    boolean requestShortcut(boolean onDesktop, boolean inMenu, String subMenu);
    boolean hasDesktopShortcut();
    boolean hasMenuShortcut();
    boolean removeShortcuts();
    boolean requestAssociation(String mimeType, String[] extensions);
    boolean hasAssociation(String mimeType, String[] extensions);
    boolean removeAssociation(String mimeType, String[] extensions);
}
