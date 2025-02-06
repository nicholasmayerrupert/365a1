import tkinter as tk
from tkinter import filedialog, messagebox
import base64

class BMPViewer(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.master.geometry("500x600")  
        self.master.resizable(True, True) 
        self.pack()
        self.create_widgets()

        self.original_pixels = None   
        self.metadata = {}

        self.brightness_value = 100
        self.scale_value = 100     
        self.r_enabled = True      
        self.g_enabled = True      
        self.b_enabled = True      

    def create_widgets(self):
        self.open_button = tk.Button(self, text="Open BMP File", command=self.open_file)
        self.open_button.pack(pady=5)

        self.metadata_label = tk.Label(self, text="Metadata will appear here.", justify="left")
        self.metadata_label.pack(pady=5)

        self.canvas = tk.Canvas(self, bg="white")
        self.canvas.pack(pady=10, expand=True, fill=tk.BOTH)

        self.brightness_slider = tk.Scale(
            self, from_=0, to=100, orient=tk.HORIZONTAL,
            label="Brightness (%)", command=self.on_brightness_change
        )
        self.brightness_slider.set(100)
        self.brightness_slider.pack(pady=5)

        self.scale_slider = tk.Scale(
            self, from_=0, to=100, orient=tk.HORIZONTAL,
            label="Scale (%)", command=self.on_scale_change
        )
        self.scale_slider.set(100)
        self.scale_slider.pack(pady=5)

        buttons_frame = tk.Frame(self)
        buttons_frame.pack(pady=5)
        self.r_button = tk.Button(buttons_frame, text="Toggle R", command=self.toggle_r)
        self.r_button.pack(side=tk.LEFT, padx=2)
        self.g_button = tk.Button(buttons_frame, text="Toggle G", command=self.toggle_g)
        self.g_button.pack(side=tk.LEFT, padx=2)
        self.b_button = tk.Button(buttons_frame, text="Toggle B", command=self.toggle_b)
        self.b_button.pack(side=tk.LEFT, padx=2)

    def on_brightness_change(self, val):
        self.brightness_value = int(val)
        self.update_image()

    def on_scale_change(self, val):
        self.scale_value = int(val)
        self.update_image()

    def toggle_r(self):
        self.r_enabled = not self.r_enabled
        self.update_image()

    def toggle_g(self):
        self.g_enabled = not self.g_enabled
        self.update_image()

    def toggle_b(self):
        self.b_enabled = not self.b_enabled
        self.update_image()

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("BMP files", "*.bmp;*.BMP")])
        if not file_path:
            return

        try:
            with open(file_path, "rb") as f:
                bmp_bytes = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {e}")
            return

        if bmp_bytes[0:2] != b'BM':
            messagebox.showerror("Error", "Not a valid BMP file.")
            return

        try:
            self.metadata, self.original_pixels = self.parse_bmp(bmp_bytes)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse BMP file: {e}")
            return

        meta_text = (
            f"File Size: {self.metadata.get('file_size')}\n"
            f"Width: {self.metadata.get('width')}\n"
            f"Height: {self.metadata.get('height')}\n"
            f"Bits per Pixel: {self.metadata.get('bpp')}\n"
        )
        self.metadata_label.config(text=meta_text)

        self.brightness_slider.set(100)
        self.scale_slider.set(100)
        self.r_enabled = True
        self.g_enabled = True
        self.b_enabled = True

        self.update_image()

    def parse_bmp(self, bmp_bytes):
        """Parses the BMP header and pixel data.
           Returns a metadata dictionary and a 2D pixel array (top-down order)."""
        metadata = {}
        metadata['file_size'] = int.from_bytes(bmp_bytes[2:6], 'little')
        data_offset = int.from_bytes(bmp_bytes[10:14], 'little')
        metadata['data_offset'] = data_offset

        header_size = int.from_bytes(bmp_bytes[14:18], 'little')
        metadata['header_size'] = header_size
        width = int.from_bytes(bmp_bytes[18:22], 'little', signed=True)
        height = int.from_bytes(bmp_bytes[22:26], 'little', signed=True)
        metadata['width'] = width
        metadata['height'] = abs(height)
        bpp = int.from_bytes(bmp_bytes[28:30], 'little')
        metadata['bpp'] = bpp
        compression = int.from_bytes(bmp_bytes[30:34], 'little')
        if compression != 0:
            raise ValueError("Compressed BMP files are not supported.")

        colors_used = int.from_bytes(bmp_bytes[46:50], 'little')
        if colors_used == 0 and bpp <= 8:
            colors_used = 1 << bpp
        metadata['colors_used'] = colors_used

        if bpp == 24:
            pixels = self.parse_24bit(bmp_bytes, metadata)
        elif bpp == 8:
            pixels = self.parse_8bit(bmp_bytes, metadata)
        elif bpp == 4:
            pixels = self.parse_4bit(bmp_bytes, metadata)
        elif bpp == 1:
            pixels = self.parse_1bit(bmp_bytes, metadata)
        else:
            raise ValueError(f"BPP {bpp} not supported.")

        return metadata, pixels

    def parse_24bit(self, bmp_bytes, metadata):
        width = metadata['width']
        height = metadata['height']
        data_offset = metadata['data_offset']
        row_size = width * 3
        padded_row_size = ((row_size + 3) // 4) * 4
        pixels = []
        pixel_data = bmp_bytes[data_offset:]
        for row in range(height):
            row_pixels = []
            row_start = row * padded_row_size
            for col in range(width):
                idx = row_start + col * 3
                B = pixel_data[idx]
                G = pixel_data[idx + 1]
                R = pixel_data[idx + 2]
                row_pixels.append((R, G, B))
            pixels.append(row_pixels)
        if int.from_bytes(bmp_bytes[22:26], 'little', signed=True) > 0:
            pixels.reverse()
        return pixels

    def parse_8bit(self, bmp_bytes, metadata):
        width = metadata['width']
        height = metadata['height']
        data_offset = metadata['data_offset']
        header_size = metadata['header_size']
        colors_used = metadata['colors_used']
        color_table = []
        ct_start = 14 + header_size
        for i in range(colors_used):
            entry = bmp_bytes[ct_start + i * 4: ct_start + i * 4 + 4]
            B, G, R, _ = entry[0], entry[1], entry[2], entry[3]
            color_table.append((R, G, B))
        row_size = width  
        padded_row_size = ((row_size + 3) // 4) * 4
        pixels = []
        pixel_data = bmp_bytes[data_offset:]
        for row in range(height):
            row_pixels = []
            row_start = row * padded_row_size
            for col in range(width):
                index = pixel_data[row_start + col]
                row_pixels.append(color_table[index])
            pixels.append(row_pixels)
        if int.from_bytes(bmp_bytes[22:26], 'little', signed=True) > 0:
            pixels.reverse()
        return pixels

    def parse_4bit(self, bmp_bytes, metadata):
        width = metadata['width']
        height = metadata['height']
        data_offset = metadata['data_offset']
        header_size = metadata['header_size']
        colors_used = metadata['colors_used']
        color_table = []
        ct_start = 14 + header_size
        for i in range(colors_used):
            entry = bmp_bytes[ct_start + i * 4: ct_start + i * 4 + 4]
            B, G, R, _ = entry[0], entry[1], entry[2], entry[3]
            color_table.append((R, G, B))
        row_bytes = (width + 1) // 2 
        padded_row_size = ((row_bytes + 3) // 4) * 4
        pixels = []
        pixel_data = bmp_bytes[data_offset:]
        for row in range(height):
            row_pixels = []
            row_start = row * padded_row_size
            for col in range(width):
                byte_val = pixel_data[row_start + (col // 2)]
                if col % 2 == 0:
                    index = byte_val >> 4
                else:
                    index = byte_val & 0x0F
                row_pixels.append(color_table[index])
            pixels.append(row_pixels)
        if int.from_bytes(bmp_bytes[22:26], 'little', signed=True) > 0:
            pixels.reverse()
        return pixels

    def parse_1bit(self, bmp_bytes, metadata):
        width = metadata['width']
        height = metadata['height']
        data_offset = metadata['data_offset']
        header_size = metadata['header_size']
        colors_used = metadata['colors_used']
        color_table = []
        ct_start = 14 + header_size
        for i in range(colors_used):
            entry = bmp_bytes[ct_start + i * 4: ct_start + i * 4 + 4]
            B, G, R, _ = entry[0], entry[1], entry[2], entry[3]
            color_table.append((R, G, B))
        row_bytes = (width + 7) // 8 
        padded_row_size = ((row_bytes + 3) // 4) * 4
        pixels = []
        pixel_data = bmp_bytes[data_offset:]
        for row in range(height):
            row_pixels = []
            row_start = row * padded_row_size
            for col in range(width):
                byte_val = pixel_data[row_start + (col // 8)]
                bit_index = 7 - (col % 8)  
                bit = (byte_val >> bit_index) & 1
                row_pixels.append(color_table[bit])
            pixels.append(row_pixels)
        if int.from_bytes(bmp_bytes[22:26], 'little', signed=True) > 0:
            pixels.reverse()
        return pixels

    def update_image(self):
        if self.original_pixels is None:
            return

        transformed = []
        for row in self.original_pixels:
            new_row = []
            for pixel in row:
                R, G, B = pixel
                R = R if self.r_enabled else 0
                G = G if self.g_enabled else 0
                B = B if self.b_enabled else 0
                factor = self.brightness_value / 100.0
                R = max(0, min(255, int(R * factor)))
                G = max(0, min(255, int(G * factor)))
                B = max(0, min(255, int(B * factor)))
                new_row.append((R, G, B))
            transformed.append(new_row)

        scaled = self.scale_image(transformed, self.scale_value)

        ppm_data = self.generate_ppm(scaled)
        try:
            ppm_str = ppm_data.decode('latin-1')
            self.photo = tk.PhotoImage(data=ppm_str, format="PPM")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL)) 
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update image: {e}")


    def scale_image(self, pixels, scale_percent):
    
        if scale_percent <= 0:
            return [[(0, 0, 0)]]
        orig_height = len(pixels)
        orig_width = len(pixels[0]) if orig_height > 0 else 0
        new_width = max(1, int(orig_width * scale_percent / 100))
        new_height = max(1, int(orig_height * scale_percent / 100))
        new_pixels = []
        for y in range(new_height):
            orig_y = int(y * orig_height / new_height)
            row = []
            for x in range(new_width):
                orig_x = int(x * orig_width / new_width)
                row.append(pixels[orig_y][orig_x])
            new_pixels.append(row)
        return new_pixels

    def generate_ppm(self, pixels):
        height = len(pixels)
        width = len(pixels[0]) if height > 0 else 0
        header = f"P6\n{width} {height}\n255\n".encode('ascii')
        data = bytearray()
        for row in pixels:
            for (R, G, B) in row:
                data.extend(bytes((R, G, B)))
        return header + data

if __name__ == "__main__":
    root = tk.Tk()
    root.title("BMP Viewer")
    app = BMPViewer(root)
    root.mainloop()
