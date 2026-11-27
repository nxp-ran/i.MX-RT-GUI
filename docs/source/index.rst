i.MX RT GUI
===========

从点亮屏幕到高性能 GUI，本系列沿着 i.MX RT 的完整像素数据路径展开：
屏幕接口、显示控制器、存储系统、PXP/GPU 与 LVGL。

建议先阅读 :doc:`系列总纲 <imxrt-gui/README>`。
点击正文顶部的 ``English`` 按钮，可以阅读当前页面的完整英文版。

.. note::

   系列共 24 篇，已提供全部中英文正文。
   理论、主机软件示例和验证方法均明确区别于板卡实测。

.. toctree::
   :maxdepth: 1
   :caption: 系列总纲

   imxrt-gui/README

.. toctree::
   :maxdepth: 1
   :caption: GUI 系统基础

   imxrt-gui/01-gui-system-overview
   imxrt-gui/02-platform-selection
   imxrt-gui/03-memory-and-bandwidth

.. toctree::
   :maxdepth: 1
   :caption: 屏幕接口

   imxrt-gui/04-spi-qspi-display

   imxrt-gui/05-flexio-dbi-display
   imxrt-gui/06-rgb-display
   imxrt-gui/07-mipi-dsi-display
   imxrt-gui/08-display-bring-up

.. toctree::
   :maxdepth: 1
   :caption: 显示外设与数据通路

   imxrt-gui/09-lcdif-elcdif

   imxrt-gui/10-memory-system
   imxrt-gui/11-buffering-and-tearing
   imxrt-gui/12-cache-mpu-dma

.. toctree::
   :maxdepth: 1
   :caption: PXP 与 GPU 硬件加速

   imxrt-gui/13-pxp-capabilities
   imxrt-gui/14-pxp-pipeline
   imxrt-gui/15-gpu-vglite
   imxrt-gui/16-render-backend-selection

.. toctree::
   :maxdepth: 1
   :caption: LVGL 移植与工程

   imxrt-gui/17-lvgl-minimal-port
   imxrt-gui/18-lvgl-refresh
   imxrt-gui/19-lvgl-acceleration
   imxrt-gui/20-touch-rtos
   imxrt-gui/21-images-fonts

.. toctree::
   :maxdepth: 1
   :caption: 性能分析与完整案例

   imxrt-gui/22-performance-testing
   imxrt-gui/23-bottleneck-optimization
   imxrt-gui/24-complete-gui-case

.. toctree::
   :maxdepth: 1
   :caption: 写作指南

   markdown
