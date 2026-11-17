package javax.jnlp;
public interface SingleInstanceService {
    void addSingleInstanceListener(SingleInstanceListener l);
    void removeSingleInstanceListener(SingleInstanceListener l);
}
