i.MX RT GUI
===========

From lighting up a display to building a high-performance GUI, this series
follows the complete pixel data path on i.MX RT:
display interfaces, display controllers, memory, PXP/GPU and LVGL.

Start with the :doc:`series outline <imxrt-gui/README>` for the full roadmap.
Use the language button above the page content to read the same page in Chinese.

.. note::

   The outline covers 24 planned articles. The outline and first nine full
   articles are available in both Chinese and English. Theory and calculation
   examples are distinguished from board-specific measurements.

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

.. toctree::
   :maxdepth: 1
   :caption: Writing guide

   markdown
