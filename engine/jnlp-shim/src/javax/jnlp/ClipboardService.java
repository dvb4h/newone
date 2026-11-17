package javax.jnlp;
import java.awt.datatransfer.Transferable;
public interface ClipboardService {
    Transferable getContents();
    void setContents(Transferable contents);
}
