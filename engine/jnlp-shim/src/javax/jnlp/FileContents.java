package javax.jnlp;
import java.io.*;
public interface FileContents {
    String getName() throws IOException;
    InputStream getInputStream() throws IOException;
    OutputStream getOutputStream(boolean overwrite) throws IOException;
    long getLength() throws IOException;
    boolean canRead() throws IOException;
    boolean canWrite() throws IOException;
    JNLPRandomAccessFile getRandomAccessFile(String mode) throws IOException;
    long getMaxLength() throws IOException;
    long setMaxLength(long maxlength) throws IOException;
}
