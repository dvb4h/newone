package javax.jnlp;
import java.net.URL;
public interface DownloadServiceListener {
    void progress(URL url, String version, long readSoFar, long total, int overallPercent);
    void validating(URL url, String version, long entry, long total, int overallPercent);
    void upgradingArchive(URL url, String version, int patchPercent, int overallPercent);
    void downloadFailed(URL url, String version);
}
