import os
import shutil
import streamlit as st
from yt_dlp import YoutubeDL

# Cloud Server ပေါ်မှာ ယာယီသိမ်းမယ့် Folder (စက်ထဲမှာ စမ်းရင်လည်း အလုပ်လုပ်ပါတယ်)
TMP_DOWNLOAD_DIR = os.path.join(os.getcwd(), "tmp_downloads")
os.makedirs(TMP_DOWNLOAD_DIR, exist_ok=True)

class StreamlitLogger:
    def __init__(self, status_box, max_lines=100):
        self.status_box = status_box
        self.max_lines = max_lines
        self.log_history = []

    def _update_ui(self):
        self.log_history = self.log_history[-self.max_lines:]
        self.status_box.code("\n".join(self.log_history))

    def debug(self, msg):
        if "[download]" in msg or "[Merger]" in msg or "Extracting" in msg:
            if "% of" not in msg:
                self.log_history.append(f"⏳ {msg}")
                self._update_ui()

    def warning(self, msg):
        pass

    def error(self, msg):
        self.log_history.append(f"❌ {msg}")
        self._update_ui()

# ==========================================
# DOWNLOAD SINGLE PLAYLIST TO SERVER
# ==========================================
def download_playlist_to_server(playlist_url, log_box, metrics_box, progress_bar, playlist_info_dict):
    st_logger = StreamlitLogger(log_box, max_lines=100)
    
    def progress_callback(d):
        if d.get('status') == 'downloading':
            info = d.get('info_dict', {})
            playlist_index = info.get('playlist_index')
            n_entries = info.get('n_entries') 
            
            # Playlist Title ကို သိမ်းထားရန်
            if 'playlist_title' in info and info['playlist_title']:
                playlist_info_dict['title'] = info['playlist_title']
            
            if playlist_index is not None and n_entries is not None:
                current = int(playlist_index)
                total = int(n_entries)
                remaining = total - current
                
                metrics_box.markdown(
                    f"### 📈 Video Progress Summary\n"
                    f"* **🟢 Done:** `{current}`\n"
                    f"* **⏳ Remaining:** `{remaining}`\n"
                    f"* **📊 Total Videos:** `{total}`"
                )
                
                progress_bar.progress(current / total)

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        # Server ပေါ်မှာ Playlist Name နဲ့ Folder ဆောက်ပြီး ဒေါင်းပါမယ်
        'outtmpl': os.path.join(TMP_DOWNLOAD_DIR, '%(playlist_title)s', '%(playlist_index)s - %(title)s.%(ext)s'),
        
        'ignoreerrors': True,
        'continuedl': True,         
        'no_overwrites': True,       
        'retries': 10,               
        'fragment_retries': 10,      
        'retry_sleep': 5,            
        'logger': st_logger,        
        'progress_hooks': [progress_callback], 
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([playlist_url])

# ==========================================
# STREAMLIT INTERFACE
# ==========================================
def main():
    st.set_page_config(page_title="YouTube Playlist Downloader", page_icon="🎬", layout="centered")
    
    st.title("🎬 YouTube Playlist Downloader")
    st.write("Enter a YouTube playlist link below. The app will download it to the server first, and then allow you to save it as a ZIP file to your computer.")
    
    playlist_url = st.text_input(
        label="Playlist URL", 
        placeholder="https://www.youtube.com/playlist?list=..."
    ).strip()
    
    # Session state သုံးပြီး ဒေါင်းလုဒ်ဆွဲပြီးသား Zip ဖိုင်လမ်းကြောင်းကို မှတ်ထားပါမယ်
    if "zip_file_path" not in st.session_state:
        st.session_state.zip_file_path = None
    if "playlist_folder_name" not in st.session_state:
        st.session_state.playlist_folder_name = None

    if st.button("🚀 Download Playlist to Cloud Server", use_container_width=True):
        if not playlist_url:
            st.warning("Please enter a valid YouTube playlist URL before proceeding.")
            return
            
        if "playlist?list=" not in playlist_url and "&list=" not in playlist_url:
            st.error("The provided URL does not seem to contain a valid YouTube playlist ID.")
            return

        # အရင်အကြိမ်က ကျန်ခဲ့တဲ့ ယာယီဖိုင်ဟောင်းတွေကို ရှင်းထုတ်ပစ်ပါမယ်
        if os.path.exists(TMP_DOWNLOAD_DIR):
            shutil.rmtree(TMP_DOWNLOAD_DIR)
        os.makedirs(TMP_DOWNLOAD_DIR, exist_ok=True)

        status_header = st.empty()
        metrics_box = st.empty()
        progress_bar = st.progress(0)
        log_box = st.empty()
        
        status_header.subheader("🔄 Connecting to YouTube & Extracting Playlist...")
        
        playlist_info = {'title': 'Downloaded_Playlist'}
        
        try:
            # ၁။ Server ပေါ်ကို အရင်ဒေါင်းလုဒ်ဆွဲမယ်
            download_playlist_to_server(playlist_url, log_box, metrics_box, progress_bar, playlist_info)
            
            playlist_name = playlist_info['title']
            target_folder = os.path.join(TMP_DOWNLOAD_DIR, playlist_name)
            
            if os.path.exists(target_folder) and os.listdir(target_folder):
                status_header.subheader("📦 Zipping folder for your local download...")
                
                # ၂။ ပြီးသွားတဲ့ Playlist Folder ကို .zip ဖိုင် ချုပ်လိုက်မယ်
                zip_output_base = os.path.join(os.getcwd(), playlist_name)
                zip_archive_path = shutil.make_archive(zip_output_base, 'zip', target_folder)
                
                st.session_state.zip_file_path = zip_archive_path
                st.session_state.playlist_folder_name = playlist_name + ".zip"
                
                status_header.success("🎉 Processed successfully on server! Ready to save on your computer.")
                progress_bar.progress(1.0)
            else:
                status_header.error("❌ No videos were downloaded. The playlist might be private or blocked.")
                
        except Exception as e:
            status_header.error(f"❌ An error occurred: {e}")

    # ==========================================
    # USER စက်ထဲသို့ ဒေါင်းလုဒ်ဆွဲရန် ခလုတ် (Browser Download)
    # ==========================================
    if st.session_state.zip_file_path and os.path.exists(st.session_state.zip_file_path):
        st.write("---")
        st.subheader("💾 Download to Your Computer")
        
        with open(st.session_state.zip_file_path, "rb") as f:
            st.download_button(
                label="📥 Click Here to Download ZIP File",
                data=f,
                file_name=st.session_state.playlist_folder_name,
                mime="application/zip",
                use_container_width=True
            )

if __name__ == "__main__":
    main()