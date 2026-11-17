package javax.jnlp;
import java.io.IOException;
import java.net.URL;
public interface DownloadService {
    boolean isResourceCached(URL ref, String version);
    boolean isPartCached(String part);
    boolean isPartCached(String[] parts);
    boolean isExtensionPartCached(URL ref, String version, String part);
    boolean isExtensionPartCached(URL ref, String version, String[] parts);
    void loadResource(URL ref, String version, DownloadServiceListener progress) throws IOException;
    void loadPart(String part, DownloadServiceListener progress) throws IOException;
    void loadPart(String[] parts, DownloadServiceListener progress) throws IOException;
    void loadExtensionPart(URL ref, String version, String part, DownloadServiceListener progress) throws IOException;
    void loadExtensionPart(URL ref, String version, String[] parts, DownloadServiceListener progress) throws IOException;
    void removeResource(URL ref, String version) throws IOException;
    void removePart(String part) throws IOException;
    void removePart(String[] parts) throws IOException;
    void removeExtensionPart(URL ref, String version, String part) throws IOException;
    void removeExtensionPart(URL ref, String version, String[] parts) throws IOException;
    DownloadServiceListener getDefaultProgressWindow();
}
