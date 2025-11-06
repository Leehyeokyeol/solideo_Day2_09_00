#!/usr/bin/env python3
"""
System Resource Monitoring System
Real-time monitoring with visualization and PDF report generation
"""

import os
import sys

# Set matplotlib to use non-interactive backend for headless environments
import matplotlib
matplotlib.use('Agg')

import psutil
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.gridspec import GridSpec
from datetime import datetime
import time
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import os
import sys

# Try to import GPUtil for GPU monitoring
try:
    import GPUtil
    GPU_AVAILABLE = True
except:
    GPU_AVAILABLE = False
    print("GPUtil not available - GPU monitoring will be skipped")


class SystemMonitor:
    """Real-time system resource monitor with visualization"""

    def __init__(self, duration=120):
        """
        Initialize the monitor

        Args:
            duration: Monitoring duration in seconds (default 120 = 2 minutes)
        """
        self.duration = duration
        self.interval = 1  # Update interval in seconds

        # Data storage
        self.timestamps = []
        self.cpu_percent = []
        self.memory_percent = []
        self.disk_read = []
        self.disk_write = []
        self.network_sent = []
        self.network_recv = []
        self.cpu_temp = []
        self.gpu_util = []
        self.gpu_temp = []
        self.gpu_memory = []

        # Initial values for network/disk delta calculation
        self.last_net = psutil.net_io_counters()
        self.last_disk = psutil.disk_io_counters()
        self.start_time = time.time()

    def setup_plot(self):
        """Setup the matplotlib figure with subplots"""
        self.fig = plt.figure(figsize=(16, 10))
        self.fig.suptitle('System Resource Monitor - Real-time',
                         fontsize=16, fontweight='bold')

        # Create grid layout
        gs = GridSpec(3, 3, figure=self.fig, hspace=0.4, wspace=0.3)

        # Create subplots
        self.ax_cpu = self.fig.add_subplot(gs[0, 0])
        self.ax_memory = self.fig.add_subplot(gs[0, 1])
        self.ax_disk_io = self.fig.add_subplot(gs[0, 2])
        self.ax_network = self.fig.add_subplot(gs[1, 0])
        self.ax_cpu_temp = self.fig.add_subplot(gs[1, 1])
        self.ax_gpu = self.fig.add_subplot(gs[1, 2])
        self.ax_summary = self.fig.add_subplot(gs[2, :])

        # Style settings
        for ax in [self.ax_cpu, self.ax_memory, self.ax_disk_io,
                   self.ax_network, self.ax_cpu_temp, self.ax_gpu]:
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, 105)

        self.ax_summary.axis('off')

    def get_cpu_temp(self):
        """Get CPU temperature if available"""
        try:
            temps = psutil.sensors_temperatures()
            if 'coretemp' in temps:
                return temps['coretemp'][0].current
            elif 'cpu_thermal' in temps:
                return temps['cpu_thermal'][0].current
            elif temps:
                # Return first available temperature
                return list(temps.values())[0][0].current
        except:
            pass
        return None

    def get_gpu_info(self):
        """Get GPU information if available"""
        if not GPU_AVAILABLE:
            return None, None, None

        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # Get first GPU
                return gpu.load * 100, gpu.temperature, gpu.memoryUtil * 100
        except:
            pass
        return None, None, None

    def collect_data(self):
        """Collect current system metrics"""
        current_time = time.time() - self.start_time
        self.timestamps.append(current_time)

        # CPU
        cpu = psutil.cpu_percent(interval=0.1)
        self.cpu_percent.append(cpu)

        # Memory
        memory = psutil.virtual_memory().percent
        self.memory_percent.append(memory)

        # Disk I/O
        disk = psutil.disk_io_counters()
        if disk and self.last_disk:
            disk_read_rate = (disk.read_bytes - self.last_disk.read_bytes) / (1024 * 1024)  # MB/s
            disk_write_rate = (disk.write_bytes - self.last_disk.write_bytes) / (1024 * 1024)  # MB/s
            self.disk_read.append(disk_read_rate)
            self.disk_write.append(disk_write_rate)
            self.last_disk = disk
        else:
            self.disk_read.append(0)
            self.disk_write.append(0)

        # Network
        net = psutil.net_io_counters()
        net_sent_rate = (net.bytes_sent - self.last_net.bytes_sent) / (1024 * 1024)  # MB/s
        net_recv_rate = (net.bytes_recv - self.last_net.bytes_recv) / (1024 * 1024)  # MB/s
        self.network_sent.append(net_sent_rate)
        self.network_recv.append(net_recv_rate)
        self.last_net = net

        # CPU Temperature
        temp = self.get_cpu_temp()
        self.cpu_temp.append(temp if temp else 0)

        # GPU
        gpu_util, gpu_temp, gpu_mem = self.get_gpu_info()
        self.gpu_util.append(gpu_util if gpu_util else 0)
        self.gpu_temp.append(gpu_temp if gpu_temp else 0)
        self.gpu_memory.append(gpu_mem if gpu_mem else 0)

    def update_plot(self, frame):
        """Update the plot with new data"""
        # Collect new data
        self.collect_data()

        # Check if monitoring duration exceeded
        if self.timestamps[-1] >= self.duration:
            plt.close(self.fig)
            return

        # Clear all axes
        self.ax_cpu.clear()
        self.ax_memory.clear()
        self.ax_disk_io.clear()
        self.ax_network.clear()
        self.ax_cpu_temp.clear()
        self.ax_gpu.clear()
        self.ax_summary.clear()

        # Plot CPU
        self.ax_cpu.plot(self.timestamps, self.cpu_percent, 'b-', linewidth=2)
        self.ax_cpu.fill_between(self.timestamps, self.cpu_percent, alpha=0.3)
        self.ax_cpu.set_title('CPU Usage (%)', fontweight='bold')
        self.ax_cpu.set_ylabel('Usage (%)')
        self.ax_cpu.set_ylim(0, 105)
        self.ax_cpu.grid(True, alpha=0.3)

        # Plot Memory
        self.ax_memory.plot(self.timestamps, self.memory_percent, 'g-', linewidth=2)
        self.ax_memory.fill_between(self.timestamps, self.memory_percent, alpha=0.3, color='green')
        self.ax_memory.set_title('Memory Usage (%)', fontweight='bold')
        self.ax_memory.set_ylabel('Usage (%)')
        self.ax_memory.set_ylim(0, 105)
        self.ax_memory.grid(True, alpha=0.3)

        # Plot Disk I/O
        self.ax_disk_io.plot(self.timestamps, self.disk_read, 'r-', label='Read', linewidth=2)
        self.ax_disk_io.plot(self.timestamps, self.disk_write, 'orange', label='Write', linewidth=2)
        self.ax_disk_io.set_title('Disk I/O (MB/s)', fontweight='bold')
        self.ax_disk_io.set_ylabel('MB/s')
        self.ax_disk_io.legend(loc='upper right')
        self.ax_disk_io.set_ylim(0, max(max(self.disk_read + [1]), max(self.disk_write + [1])) * 1.2)
        self.ax_disk_io.grid(True, alpha=0.3)

        # Plot Network
        self.ax_network.plot(self.timestamps, self.network_sent, 'purple', label='Sent', linewidth=2)
        self.ax_network.plot(self.timestamps, self.network_recv, 'cyan', label='Received', linewidth=2)
        self.ax_network.set_title('Network Traffic (MB/s)', fontweight='bold')
        self.ax_network.set_ylabel('MB/s')
        self.ax_network.legend(loc='upper right')
        self.ax_network.set_ylim(0, max(max(self.network_sent + [1]), max(self.network_recv + [1])) * 1.2)
        self.ax_network.grid(True, alpha=0.3)

        # Plot CPU Temperature
        if any(t > 0 for t in self.cpu_temp):
            self.ax_cpu_temp.plot(self.timestamps, self.cpu_temp, 'red', linewidth=2)
            self.ax_cpu_temp.fill_between(self.timestamps, self.cpu_temp, alpha=0.3, color='red')
            self.ax_cpu_temp.set_title('CPU Temperature (°C)', fontweight='bold')
            self.ax_cpu_temp.set_ylabel('Temperature (°C)')
            self.ax_cpu_temp.set_ylim(0, max(self.cpu_temp + [100]) * 1.1)
        else:
            self.ax_cpu_temp.text(0.5, 0.5, 'Temperature\nNot Available',
                                 ha='center', va='center', transform=self.ax_cpu_temp.transAxes,
                                 fontsize=12)
        self.ax_cpu_temp.grid(True, alpha=0.3)

        # Plot GPU
        if GPU_AVAILABLE and any(g > 0 for g in self.gpu_util):
            self.ax_gpu.plot(self.timestamps, self.gpu_util, 'magenta', label='GPU Usage', linewidth=2)
            self.ax_gpu.plot(self.timestamps, self.gpu_memory, 'brown', label='GPU Memory', linewidth=2)
            self.ax_gpu.set_title('GPU Usage & Memory (%)', fontweight='bold')
            self.ax_gpu.set_ylabel('Usage (%)')
            self.ax_gpu.legend(loc='upper right')
            self.ax_gpu.set_ylim(0, 105)
        else:
            self.ax_gpu.text(0.5, 0.5, 'GPU\nNot Available',
                           ha='center', va='center', transform=self.ax_gpu.transAxes,
                           fontsize=12)
        self.ax_gpu.grid(True, alpha=0.3)

        # Summary text
        self.ax_summary.axis('off')
        current_cpu = self.cpu_percent[-1]
        current_mem = self.memory_percent[-1]
        elapsed = self.timestamps[-1]
        remaining = self.duration - elapsed

        summary_text = f"""
        Current Status (Elapsed: {elapsed:.1f}s / {self.duration}s - Remaining: {remaining:.1f}s)
        ═══════════════════════════════════════════════════════════════════════════════
        CPU: {current_cpu:.1f}%  |  Memory: {current_mem:.1f}%  |
        Disk R/W: {self.disk_read[-1]:.2f}/{self.disk_write[-1]:.2f} MB/s  |
        Network S/R: {self.network_sent[-1]:.2f}/{self.network_recv[-1]:.2f} MB/s
        """

        self.ax_summary.text(0.5, 0.5, summary_text,
                           ha='center', va='center',
                           transform=self.ax_summary.transAxes,
                           fontsize=11, family='monospace',
                           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()

    def generate_pdf_report(self, filename='system_monitor_report.pdf'):
        """Generate a comprehensive PDF report"""
        print(f"\nGenerating PDF report: {filename}")

        # Create document
        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            alignment=TA_CENTER,
            spaceAfter=30
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2d5aa6'),
            spaceAfter=12
        )

        # Title
        title = Paragraph("System Resource Monitoring Report", title_style)
        elements.append(title)

        # Monitoring info
        info_text = f"""
        <b>Monitoring Duration:</b> {self.duration} seconds ({self.duration/60:.1f} minutes)<br/>
        <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
        <b>Data Points Collected:</b> {len(self.timestamps)}<br/>
        <b>Update Interval:</b> {self.interval} second(s)
        """
        elements.append(Paragraph(info_text, styles['Normal']))
        elements.append(Spacer(1, 20))

        # Summary Statistics Table
        elements.append(Paragraph("Summary Statistics", heading_style))

        summary_data = [
            ['Resource', 'Average', 'Minimum', 'Maximum', 'Std Dev'],
            ['CPU Usage (%)', f'{np.mean(self.cpu_percent):.2f}',
             f'{np.min(self.cpu_percent):.2f}', f'{np.max(self.cpu_percent):.2f}',
             f'{np.std(self.cpu_percent):.2f}'],
            ['Memory Usage (%)', f'{np.mean(self.memory_percent):.2f}',
             f'{np.min(self.memory_percent):.2f}', f'{np.max(self.memory_percent):.2f}',
             f'{np.std(self.memory_percent):.2f}'],
            ['Disk Read (MB/s)', f'{np.mean(self.disk_read):.2f}',
             f'{np.min(self.disk_read):.2f}', f'{np.max(self.disk_read):.2f}',
             f'{np.std(self.disk_read):.2f}'],
            ['Disk Write (MB/s)', f'{np.mean(self.disk_write):.2f}',
             f'{np.min(self.disk_write):.2f}', f'{np.max(self.disk_write):.2f}',
             f'{np.std(self.disk_write):.2f}'],
            ['Network Sent (MB/s)', f'{np.mean(self.network_sent):.2f}',
             f'{np.min(self.network_sent):.2f}', f'{np.max(self.network_sent):.2f}',
             f'{np.std(self.network_sent):.2f}'],
            ['Network Recv (MB/s)', f'{np.mean(self.network_recv):.2f}',
             f'{np.min(self.network_recv):.2f}', f'{np.max(self.network_recv):.2f}',
             f'{np.std(self.network_recv):.2f}'],
        ]

        # Add CPU temp if available
        if any(t > 0 for t in self.cpu_temp):
            summary_data.append(['CPU Temperature (°C)', f'{np.mean(self.cpu_temp):.2f}',
                               f'{np.min(self.cpu_temp):.2f}', f'{np.max(self.cpu_temp):.2f}',
                               f'{np.std(self.cpu_temp):.2f}'])

        # Add GPU if available
        if GPU_AVAILABLE and any(g > 0 for g in self.gpu_util):
            summary_data.append(['GPU Utilization (%)', f'{np.mean(self.gpu_util):.2f}',
                               f'{np.min(self.gpu_util):.2f}', f'{np.max(self.gpu_util):.2f}',
                               f'{np.std(self.gpu_util):.2f}'])
            summary_data.append(['GPU Memory (%)', f'{np.mean(self.gpu_memory):.2f}',
                               f'{np.min(self.gpu_memory):.2f}', f'{np.max(self.gpu_memory):.2f}',
                               f'{np.std(self.gpu_memory):.2f}'])
            summary_data.append(['GPU Temperature (°C)', f'{np.mean(self.gpu_temp):.2f}',
                               f'{np.min(self.gpu_temp):.2f}', f'{np.max(self.gpu_temp):.2f}',
                               f'{np.std(self.gpu_temp):.2f}'])

        table = Table(summary_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d5aa6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ]))
        elements.append(table)
        elements.append(PageBreak())

        # Generate graphs
        elements.append(Paragraph("Resource Usage Graphs", heading_style))

        # Create figure for PDF graphs
        fig_pdf = plt.figure(figsize=(10, 12))
        gs = GridSpec(4, 2, figure=fig_pdf, hspace=0.4, wspace=0.3)

        # CPU Graph
        ax1 = fig_pdf.add_subplot(gs[0, 0])
        ax1.plot(self.timestamps, self.cpu_percent, 'b-', linewidth=2)
        ax1.fill_between(self.timestamps, self.cpu_percent, alpha=0.3)
        ax1.set_title('CPU Usage Over Time', fontweight='bold')
        ax1.set_xlabel('Time (seconds)')
        ax1.set_ylabel('Usage (%)')
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 105)

        # Memory Graph
        ax2 = fig_pdf.add_subplot(gs[0, 1])
        ax2.plot(self.timestamps, self.memory_percent, 'g-', linewidth=2)
        ax2.fill_between(self.timestamps, self.memory_percent, alpha=0.3, color='green')
        ax2.set_title('Memory Usage Over Time', fontweight='bold')
        ax2.set_xlabel('Time (seconds)')
        ax2.set_ylabel('Usage (%)')
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(0, 105)

        # Disk I/O Graph
        ax3 = fig_pdf.add_subplot(gs[1, 0])
        ax3.plot(self.timestamps, self.disk_read, 'r-', label='Read', linewidth=2)
        ax3.plot(self.timestamps, self.disk_write, 'orange', label='Write', linewidth=2)
        ax3.set_title('Disk I/O Over Time', fontweight='bold')
        ax3.set_xlabel('Time (seconds)')
        ax3.set_ylabel('MB/s')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # Network Graph
        ax4 = fig_pdf.add_subplot(gs[1, 1])
        ax4.plot(self.timestamps, self.network_sent, 'purple', label='Sent', linewidth=2)
        ax4.plot(self.timestamps, self.network_recv, 'cyan', label='Received', linewidth=2)
        ax4.set_title('Network Traffic Over Time', fontweight='bold')
        ax4.set_xlabel('Time (seconds)')
        ax4.set_ylabel('MB/s')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        # CPU Temperature Graph
        ax5 = fig_pdf.add_subplot(gs[2, 0])
        if any(t > 0 for t in self.cpu_temp):
            ax5.plot(self.timestamps, self.cpu_temp, 'red', linewidth=2)
            ax5.fill_between(self.timestamps, self.cpu_temp, alpha=0.3, color='red')
            ax5.set_title('CPU Temperature Over Time', fontweight='bold')
            ax5.set_xlabel('Time (seconds)')
            ax5.set_ylabel('Temperature (°C)')
            ax5.grid(True, alpha=0.3)
        else:
            ax5.text(0.5, 0.5, 'CPU Temperature\nNot Available',
                    ha='center', va='center', transform=ax5.transAxes,
                    fontsize=12)
            ax5.set_title('CPU Temperature', fontweight='bold')

        # GPU Graph
        ax6 = fig_pdf.add_subplot(gs[2, 1])
        if GPU_AVAILABLE and any(g > 0 for g in self.gpu_util):
            ax6.plot(self.timestamps, self.gpu_util, 'magenta', label='GPU Usage', linewidth=2)
            ax6.plot(self.timestamps, self.gpu_memory, 'brown', label='GPU Memory', linewidth=2)
            ax6.set_title('GPU Utilization Over Time', fontweight='bold')
            ax6.set_xlabel('Time (seconds)')
            ax6.set_ylabel('Usage (%)')
            ax6.legend()
            ax6.grid(True, alpha=0.3)
            ax6.set_ylim(0, 105)
        else:
            ax6.text(0.5, 0.5, 'GPU\nNot Available',
                    ha='center', va='center', transform=ax6.transAxes,
                    fontsize=12)
            ax6.set_title('GPU Utilization', fontweight='bold')

        # Distribution plots
        ax7 = fig_pdf.add_subplot(gs[3, 0])
        ax7.hist(self.cpu_percent, bins=20, color='blue', alpha=0.7, edgecolor='black')
        ax7.set_title('CPU Usage Distribution', fontweight='bold')
        ax7.set_xlabel('Usage (%)')
        ax7.set_ylabel('Frequency')
        ax7.grid(True, alpha=0.3)

        ax8 = fig_pdf.add_subplot(gs[3, 1])
        ax8.hist(self.memory_percent, bins=20, color='green', alpha=0.7, edgecolor='black')
        ax8.set_title('Memory Usage Distribution', fontweight='bold')
        ax8.set_xlabel('Usage (%)')
        ax8.set_ylabel('Frequency')
        ax8.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save graphs to temporary file
        graph_file = 'temp_graphs.png'
        plt.savefig(graph_file, dpi=150, bbox_inches='tight')
        plt.close(fig_pdf)

        # Add graphs to PDF
        img = Image(graph_file, width=7*inch, height=8.4*inch)
        elements.append(img)
        elements.append(PageBreak())

        # Detailed Data Table (sample - first and last 10 entries)
        elements.append(Paragraph("Detailed Data Sample (First & Last 10 Records)", heading_style))

        detailed_data = [['Time (s)', 'CPU %', 'Memory %', 'Disk R', 'Disk W', 'Net S', 'Net R']]

        # First 10 records
        for i in range(min(10, len(self.timestamps))):
            detailed_data.append([
                f'{self.timestamps[i]:.1f}',
                f'{self.cpu_percent[i]:.1f}',
                f'{self.memory_percent[i]:.1f}',
                f'{self.disk_read[i]:.2f}',
                f'{self.disk_write[i]:.2f}',
                f'{self.network_sent[i]:.2f}',
                f'{self.network_recv[i]:.2f}'
            ])

        # Add separator if we have more than 20 records
        if len(self.timestamps) > 20:
            detailed_data.append(['...', '...', '...', '...', '...', '...', '...'])

            # Last 10 records
            for i in range(max(10, len(self.timestamps)-10), len(self.timestamps)):
                detailed_data.append([
                    f'{self.timestamps[i]:.1f}',
                    f'{self.cpu_percent[i]:.1f}',
                    f'{self.memory_percent[i]:.1f}',
                    f'{self.disk_read[i]:.2f}',
                    f'{self.disk_write[i]:.2f}',
                    f'{self.network_sent[i]:.2f}',
                    f'{self.network_recv[i]:.2f}'
                ])

        detail_table = Table(detailed_data)
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d5aa6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(detail_table)

        # Build PDF
        doc.build(elements)

        # Clean up temporary graph file
        if os.path.exists(graph_file):
            os.remove(graph_file)

        print(f"PDF report generated successfully: {filename}")

    def start(self):
        """Start the monitoring process"""
        print(f"Starting system monitoring for {self.duration} seconds...")
        print(f"Data collection in progress (headless mode)...")
        print(f"Press Ctrl+C to stop early and generate report.\n")

        try:
            # Data collection loop
            start_time = time.time()
            iteration = 0

            while (time.time() - start_time) < self.duration:
                # Collect data
                self.collect_data()
                iteration += 1

                # Show progress
                elapsed = time.time() - start_time
                remaining = self.duration - elapsed
                progress = (elapsed / self.duration) * 100

                print(f"\rProgress: {progress:.1f}% | Elapsed: {elapsed:.1f}s / {self.duration}s | "
                      f"Remaining: {remaining:.1f}s | Data points: {iteration}", end='', flush=True)

                # Wait for next interval
                time.sleep(self.interval)

        except KeyboardInterrupt:
            print("\n\nMonitoring interrupted by user.")

        print("\n\nData collection complete!")

        # Generate report
        if len(self.timestamps) > 0:
            self.generate_pdf_report()
        else:
            print("No data collected. Report not generated.")


def main():
    """Main function"""
    print("=" * 70)
    print("SYSTEM RESOURCE MONITORING SYSTEM")
    print("=" * 70)
    print()

    # Create and start monitor
    monitor = SystemMonitor(duration=120)  # 2 minutes
    monitor.start()

    print("\nMonitoring complete!")
    print(f"Total data points collected: {len(monitor.timestamps)}")
    print("\nReport saved as: system_monitor_report.pdf")


if __name__ == "__main__":
    main()
