package javax.jnlp;
import java.io.IOException;
import java.net.*;
public interface PersistenceService {
    int CACHED = 0;
    int TEMPORARY = 1;
    int DIRTY = 2;
    long create(URL url, long maxsize) throws MalformedURLException, IOException;
    FileContents get(URL url) throws MalformedURLException, IOException, java.io.FileNotFoundException;
    void delete(URL url) throws MalformedURLException, IOException;
    String[] getNames(URL url) throws MalformedURLException, IOException;
    int getTag(URL url) throws MalformedURLException, IOException;
    void setTag(URL url, int tag) throws MalformedURLException, IOException;
}
