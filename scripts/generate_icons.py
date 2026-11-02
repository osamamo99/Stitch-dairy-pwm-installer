import zlib
import struct
import os

def create_png(width, height, get_pixel_func, filename):
    raw_bytes = bytearray()
    for y in range(height):
        raw_bytes.append(0)  # Filter type None
        for x in range(width):
            r, g, b, a = get_pixel_func(x, y, width, height)
            raw_bytes.extend([r, g, b, a])
    
    compressed = zlib.compress(bytes(raw_bytes), 9)
    
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    
    png = bytearray(b'\x89PNG\r\n\x1a\n')
    png.extend(chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)))
    png.extend(chunk(b'IDAT', compressed))
    png.extend(chunk(b'IEND', b''))
    
    with open(filename, 'wb') as f:
        f.write(png)
    print(f"Generated {filename} ({width}x{height})")

def stitch_diary_pixel(x, y, W, H, is_maskable=False):
    # Normalized coordinates 0.0 to 1.0
    nx = x / W
    ny = y / H
    
    # Background: vibrant blue #4a90e2 -> #2c6cb5 gradient
    bg_r = int(74 - (74 - 44) * ny)
    bg_g = int(144 - (144 - 108) * ny)
    bg_b = int(226 - (226 - 181) * ny)
    
    if is_maskable:
        # Full bleed background for adaptive icons
        r, g, b, a = bg_r, bg_g, bg_b, 255
    else:
        # Rounded corner squircle
        cx = 0.5
        cy = 0.5
        dx = abs(nx - cx) * 2
        dy = abs(ny - cy) * 2
        # Smooth rounded boundary
        power = 5.0
        dist = (dx**power + dy**power)**(1/power)
        if dist > 0.98:
            return (0, 0, 0, 0)
        r, g, b, a = bg_r, bg_g, bg_b, 255

    # Center bounding box for diary book
    # Safe zone: [0.15, 0.85] x [0.12, 0.88]
    bx0, by0, bx1, by1 = 0.16, 0.13, 0.84, 0.87
    
    # Check if inside book
    if bx0 <= nx <= bx1 and by0 <= ny <= by1:
        # Rounded corners of book
        cdx = min(nx - bx0, bx1 - nx)
        cdy = min(ny - by0, by1 - ny)
        corner_r = 0.04
        if cdx < corner_r and cdy < corner_r:
            if (cdx - corner_r)**2 + (cdy - corner_r)**2 > corner_r**2:
                # Outside book corner, return background
                return (r, g, b, a)

        # Book Spine (Dark Blue/Grey Navy) on left: [bx0, bx0 + 0.13]
        spine_x1 = bx0 + 0.13
        if nx <= spine_x1:
            # Spine background
            sr, sg, sb = 44, 62, 80 # #2c3e50
            # Gold stitch loops on spine
            # Placed at regular intervals
            stitch_y_spacing = (by1 - by0) / 9
            for k in range(1, 9):
                sy = by0 + k * stitch_y_spacing
                if abs(ny - sy) < 0.012 and abs(nx - (bx0 + 0.065)) < 0.035:
                    return (241, 196, 15, 255) # Gold stitch #f1c40f
            return (sr, sg, sb, 255)
        
        # Paper page body (White to light cream #ffffff -> #f8fafc)
        pr, pg, pb = 255, 255, 255
        
        # Top title bar: [bx0 + 0.17, bx1 - 0.05], y: [by0 + 0.05, by0 + 0.12]
        if (bx0 + 0.17) <= nx <= (bx1 - 0.05) and (by0 + 0.05) <= ny <= (by0 + 0.12):
            return (225, 245, 254, 255) # Light blue header #e1f5fe
            
        # Number Grid area: [bx0 + 0.17, bx1 - 0.05], y: [by0 + 0.16, by0 + 0.58]
        gx0, gy0, gx1, gy1 = bx0 + 0.17, by0 + 0.16, bx1 - 0.05, by0 + 0.58
        if gx0 <= nx <= gx1 and gy0 <= ny <= gy1:
            # Check grid lines
            # Outer border
            if abs(nx - gx0) < 0.005 or abs(nx - gx1) < 0.005 or abs(ny - gy0) < 0.005 or abs(ny - gy1) < 0.005:
                return (203, 213, 225, 255) # #cbd5e1 grid line
            
            # Horizontal lines (4 rows)
            row_h = (gy1 - gy0) / 4
            for r_idx in range(1, 4):
                if abs(ny - (gy0 + r_idx * row_h)) < 0.004:
                    return (203, 213, 225, 255)
            
            # Vertical lines (4 cols)
            col_w = (gx1 - gx0) / 4
            for c_idx in range(1, 4):
                if abs(nx - (gx0 + c_idx * col_w)) < 0.004:
                    return (203, 213, 225, 255)
            
            # Needle / thread stitch indicator
            # Row 0 header background
            if ny < gy0 + row_h:
                return (241, 245, 249, 255) # #f1f5f9
            
            # Cell markings
            cell_x = int((nx - gx0) / col_w)
            cell_y = int((ny - gy0) / row_h)
            # Center of each cell
            ccx = gx0 + (cell_x + 0.5) * col_w
            ccy = gy0 + (cell_y + 0.5) * row_h
            if abs(nx - ccx) < 0.015 and abs(ny - ccy) < 0.012:
                if (cell_x + cell_y) % 2 == 0:
                    return (46, 204, 113, 255) # Green stitch count
                else:
                    return (74, 144, 226, 255) # Blue stitch count
            
            return (255, 255, 255, 255)

        # Bottom summary bar: [bx0 + 0.17, bx1 - 0.05], y: [by0 + 0.63, by0 + 0.72]
        if (bx0 + 0.17) <= nx <= (bx1 - 0.05) and (by0 + 0.63) <= ny <= (by0 + 0.72):
            return (74, 144, 226, 255) # Primary blue bar
            
        return (pr, pg, pb, 255)
        
    return (r, g, b, a)

os.makedirs('public', exist_ok=True)
create_png(192, 192, lambda x, y, w, h: stitch_diary_pixel(x, y, w, h, False), 'public/icon-192.png')
create_png(512, 512, lambda x, y, w, h: stitch_diary_pixel(x, y, w, h, False), 'public/icon-512.png')
create_png(512, 512, lambda x, y, w, h: stitch_diary_pixel(x, y, w, h, True), 'public/icon-maskable-512.png')
create_png(180, 180, lambda x, y, w, h: stitch_diary_pixel(x, y, w, h, False), 'public/apple-touch-icon.png')
create_png(48, 48, lambda x, y, w, h: stitch_diary_pixel(x, y, w, h, False), 'public/favicon.ico')
print("All PNG icons created successfully!")
