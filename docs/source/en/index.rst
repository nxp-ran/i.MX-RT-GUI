i.MX RT GUI
===========

From lighting up a display to building a high-performance GUI, this series
follows the complete pixel data path on i.MX RT:
display interfaces, display controllers, memory, PXP/GPU and LVGL.

Start with the :doc:`series outline <imxrt-gui/README>` for the full roadmap.
Use the language button above the page content to read the same page in Chinese.

.. note::

   All 24 articles are available in Chinese and English. Theory, host software
   examples and validation procedures are distinguished from board measurements.

.. toctree::
   :maxdepth: 1
   :caption: Series outline

   imxrt-gui/README

.. toctree::
   :maxdepth: 1
   :caption: GUI fundamentals

   imxrt-gui/01-gui-system-overview
   imxrt-gui/02-platform-selection
   imxrt-gui/03-memory-and-bandwidth

.. toctree::
   :maxdepth: 1
   :caption: Display interfaces

   imxrt-gui/04-spi-qspi-display

   imxrt-gui/05-flexio-dbi-display
   imxrt-gui/06-rgb-display
   imxrt-gui/07-mipi-dsi-display
   imxrt-gui/08-display-bring-up

.. toctree::
   :maxdepth: 1
   :caption: Display peripherals and data paths

   imxrt-gui/09-lcdif-elcdif

   imxrt-gui/10-memory-system
   imxrt-gui/11-buffering-and-tearing
   imxrt-gui/12-cache-mpu-dma

.. toctree::
   :maxdepth: 1
   :caption: PXP and GPU acceleration

   imxrt-gui/13-pxp-capabilities
   imxrt-gui/14-pxp-pipeline
   imxrt-gui/15-gpu-vglite
   imxrt-gui/16-render-backend-selection

.. toctree::
   :maxdepth: 1
   :caption: LVGL porting and engineering

   imxrt-gui/17-lvgl-minimal-port
   imxrt-gui/18-lvgl-refresh
   imxrt-gui/19-lvgl-acceleration
   imxrt-gui/20-touch-rtos
   imxrt-gui/21-images-fonts

.. toctree::
   :maxdepth: 1
   :caption: Performance and complete case

   imxrt-gui/22-performance-testing
   imxrt-gui/23-bottleneck-optimization
   imxrt-gui/24-complete-gui-case

.. toctree::
   :maxdepth: 1
   :caption: Writing guide

   markdown
