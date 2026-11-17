package javax.jnlp;
import java.io.IOException;
public interface FileOpenService {
    FileContents openFileDialog(String pathHint, String[] extensions) throws IOException;
    FileContents[] openMultiFileDialog(String pathHint, String[] extensions) throws IOException;
}
