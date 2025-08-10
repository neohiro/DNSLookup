# Import necessary modules from the tkinter library for creating the GUI.
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
# Import the socket module for network operations (DNS lookup).
import socket
# Import the re module for regular expressions to validate input.
import re
# Import os and datetime for file path manipulation and timestamps.
import os
import datetime
# Import the threading module to run lookups on a separate thread.
import threading

class DnsLookupApp(tk.Tk):
    """
    A GUI application for performing DNS lookups and reverse DNS lookups.
    """
    def __init__(self):
        # Initialize the main application window.
        super().__init__()

        # --- Window Configuration ---
        self.title("DNS Lookup Tool")
        self.geometry("600x400") # Set the initial size of the window.
        self.configure(bg="#2c3e50") # A dark blue-gray background color for a sleek look.
        
        # Set the application icon. The 'icon.ico' file must be in the same directory as the script.
        try:
            self.iconbitmap("icon.ico")
        except tk.TclError:
            # This handles the case where the icon file is not found.
            print("Warning: 'icon.ico' file not found. The application will run without an icon.")

        # --- Styling (Theming) ---
        # A sleek theme using ttk widgets for a more modern appearance.
        style = ttk.Style(self)
        style.theme_use('clam') # Use a clean, modern theme.
        style.configure('TFrame', background="#2c3e50")
        style.configure('TLabel', background="#2c3e50", foreground="#ecf0f1", font=("Inter", 12))
        style.configure('TButton', background="#3498db", foreground="white", font=("Inter", 12, 'bold'), borderwidth=1, focuscolor="#2980b9")
        style.map('TButton', background=[('active', '#2980b9')])
        style.configure('TEntry', fieldbackground="#34495e", foreground="#ecf0f1", borderwidth=1, relief="flat", font=("Inter", 12))

        # --- UI Layout ---
        # Create a main frame to hold all other widgets, providing structure.
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create a label to instruct the user.
        label = ttk.Label(main_frame, text="Enter a domain name or IP address:")
        label.pack(pady=(0, 10))

        # Create an input field (Entry) for the user to type in their query.
        self.entry = ttk.Entry(main_frame, width=50)
        self.entry.pack(pady=(0, 10), ipady=5)
        # Bind the Enter key to the lookup function for convenience.
        self.entry.bind("<Return>", lambda event: self.perform_lookup())

        # Create a frame for the buttons to keep them together.
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(0, 20))

        # Create a button that triggers the DNS lookup function when clicked.
        # This button will now act as a toggle between "Lookup" and "Cancel Lookup".
        self.lookup_button = ttk.Button(button_frame, text="Lookup", command=self.perform_lookup)
        self.lookup_button.pack(side=tk.LEFT, padx=(0, 10))

        # Create the new "Save to Log" button.
        self.save_button = ttk.Button(button_frame, text="Save to Log", command=self.save_to_log)
        self.save_button.pack(side=tk.LEFT)

        # Create a scrolled text area to display the results.
        # This widget is ideal for multi-line output and has a built-in scrollbar.
        self.results_text = scrolledtext.ScrolledText(main_frame, width=60, height=10, relief="flat", borderwidth=0,
                                                       background="#34495e", foreground="#ecf0f1", font=("Inter", 11),
                                                       insertbackground="white")
        self.results_text.pack(fill=tk.BOTH, expand=True)

        # --- Right-click context menu for copying text ---
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self.copy_text)
        # Bind the right-click event (Button-3) to a function that shows the menu.
        self.results_text.bind("<Button-3>", self.show_context_menu)
        
        # We need a reference to the lookup thread and a unique ID to manage cancellations.
        self.lookup_thread = None
        self.lookup_id = 0

    def show_context_menu(self, event):
        """
        Displays the context menu at the mouse cursor's position.
        """
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def copy_text(self):
        """
        Copies the selected text from the results box to the clipboard.
        """
        try:
            # Check if there is selected text.
            if self.results_text.tag_ranges(tk.SEL):
                # Use event_generate to simulate a Ctrl-C keypress, which handles
                # the copy action automatically for the widget.
                self.results_text.event_generate("<<Copy>>")
        except tk.TclError:
            # Handle cases where no text is selected.
            pass

    def save_to_log(self):
        """
        Saves the content of the results box to a timestamped log file.
        This creates a new file for each save, avoiding the loss of previous logs.
        """
        # Get all text from the results box.
        log_content = self.results_text.get(1.0, tk.END).strip()

        # If there's no content to save, show a warning and exit.
        if not log_content:
            messagebox.showwarning("Warning", "The results box is empty. Please perform a lookup first.")
            return

        try:
            # Get the path to the user's Documents folder.
            documents_path = os.path.join(os.path.expanduser("~"), "Documents")
            # Create the directory if it doesn't exist.
            os.makedirs(documents_path, exist_ok=True)

            # Generate a timestamped filename to avoid overwriting files.
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            file_name = f"dns_lookup_{timestamp}.txt"
            full_path = os.path.join(documents_path, file_name)

            # Open the file in write mode ('w'). This creates a new file each time.
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(log_content)

            # Show a success message to the user.
            messagebox.showinfo("Success", f"Results saved successfully to:\n{full_path}")

        except Exception as e:
            # Handle any errors that might occur during the file-saving process.
            messagebox.showerror("Error", f"Failed to save the log file.\nDetails: {e}")

    def perform_lookup(self):
        """
        Toggles between starting a lookup and canceling a running lookup.
        """
        # Check if a lookup is currently in progress.
        if self.lookup_thread is not None and self.lookup_thread.is_alive():
            self.cancel_lookup()
            return

        # Get the query from the input field, stripping any whitespace.
        query = self.entry.get().strip()
        self.results_text.delete(1.0, tk.END)

        if not query:
            messagebox.showerror("Error", "Please enter a domain or IP address.")
            return

        # Simple validation before starting the thread.
        valid_chars_regex = r"^[a-zA-Z0-9\.\-:]+$"
        if not re.match(valid_chars_regex, query):
            messagebox.showerror("Error", "Invalid query format. Please enter a valid domain or IP address.")
            return

        # Increment the lookup ID for this new lookup.
        self.lookup_id += 1
        current_lookup_id = self.lookup_id

        # Change button state and text to "Cancel Lookup".
        self.lookup_button.config(text="Cancel Lookup")
        self.results_text.insert(tk.END, "Performing lookup... Please wait.\n")

        # Create and start a new thread for the actual lookup.
        self.lookup_thread = threading.Thread(target=self._threaded_lookup, args=(query, current_lookup_id))
        self.lookup_thread.start()

    def cancel_lookup(self):
        """
        Stops the currently running lookup and resets the GUI state.
        """
        if self.lookup_thread is not None and self.lookup_thread.is_alive():
            # This is the key change: we clear the thread reference and reset the ID.
            # This makes the main thread ready for a new lookup immediately.
            self.lookup_thread = None
            
            self.results_text.insert(tk.END, "\nLookup canceled.\n")
            self.lookup_button.config(text="Lookup")

    def _threaded_lookup(self, query, lookup_id):
        """
        Performs the DNS lookup in a separate thread.
        This function is now significantly more robust, handling both
        forward and reverse lookups and providing all available IP versions.
        """
        # Set a local timeout for this specific socket operation.
        socket.setdefaulttimeout(5)
        
        output = ""
        try:
            # Check if the query is a valid IP address.
            is_ip = False
            try:
                # Use socket.inet_pton to check for valid IPv4 or IPv6 format.
                socket.inet_pton(socket.AF_INET, query)
                is_ip = True
            except socket.error:
                try:
                    socket.inet_pton(socket.AF_INET6, query)
                    is_ip = True
                except socket.error:
                    pass

            if is_ip:
                # Case 1: The query is an IP address (IPv4 or IPv6).
                # First, perform a reverse DNS lookup to get the domain name.
                try:
                    domain, aliases, ips = socket.gethostbyaddr(query)
                    # Now perform a forward lookup on that domain to get all related IPs.
                    addr_info = socket.getaddrinfo(domain, None)
                    
                    ipv4_addresses = sorted(list(set(info[4][0] for info in addr_info if info[0] == socket.AF_INET)))
                    ipv6_addresses = sorted(list(set(info[4][0] for info in addr_info if info[0] == socket.AF_INET6)))

                    output = f"✅ Reverse Lookup for IP address '{query}':\n"
                    output += f"   Primary Domain: {domain}\n"
                    if aliases:
                        output += f"   Aliases: {', '.join(aliases)}\n"
                    
                    if ipv4_addresses:
                        output += f"\n   All IPv4 Addresses for '{domain}':\n"
                        for ip in ipv4_addresses:
                            output += f"     - {ip}\n"
                    
                    if ipv6_addresses:
                        output += f"\n   All IPv6 Addresses for '{domain}':\n"
                        for ip in ipv6_addresses:
                            output += f"     - {ip}\n"
                            
                except socket.herror:
                    output = f"❌ Error: No host found for IP address '{query}'.\n"

            else:
                # Case 2: The query is a domain name.
                # Use getaddrinfo to get all available addresses (IPv4 and IPv6).
                addr_info = socket.getaddrinfo(query, None)
                
                ipv4_addresses = sorted(list(set(info[4][0] for info in addr_info if info[0] == socket.AF_INET)))
                ipv6_addresses = sorted(list(set(info[4][0] for info in addr_info if info[0] == socket.AF_INET6)))
                
                output = f"✅ Forward Lookup for domain '{query}':\n"
                
                if ipv4_addresses:
                    output += f"\n   All IPv4 Addresses:\n"
                    for ip in ipv4_addresses:
                        output += f"     - {ip}\n"
                
                if ipv6_addresses:
                    output += f"\n   All IPv6 Addresses:\n"
                    for ip in ipv6_addresses:
                        output += f"     - {ip}\n"

        except socket.timeout:
            output = f"❌ Error: The lookup for '{query}' timed out after 5 seconds.\n"
            output += "   This may be due to a non-existent or unresponsive host.\n"
        except socket.gaierror as e:
            output = f"❌ Error: Could not resolve '{query}'.\n"
            output += f"   Details: {e}\n"
        except Exception as e:
            output = f"⚠️ An unexpected error occurred: {e}\n"
        
        # Use a method on the main thread to update the GUI.
        self.after(0, self._update_gui, output, lookup_id)

    def _update_gui(self, output, lookup_id):
        """
        Safely updates the GUI from the worker thread.
        """
        # Only update the GUI if this is the most recent lookup.
        # This prevents a canceled lookup thread from overwriting the results of a new one.
        if lookup_id != self.lookup_id:
            return

        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, output)

        # Reset the button state.
        self.lookup_button.config(text="Lookup")
        self.lookup_thread = None

if __name__ == "__main__":
    # Create an instance of the application and start the main event loop.
    app = DnsLookupApp()
    app.mainloop()
