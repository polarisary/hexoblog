---
title: Shader渲染流水线
date: 2017-03-29 14:43:43
categories: Unity #文章文类
tags: unity shader 渲染流水线 光照模型
---

GPU流水线上可高度编程的阶段，包括表面着色器、顶点片元着色器、固定管线着色器。目前的Unity5中，本质上只有顶点片元着色器

#### 关于渲染流水线：

主要任务：从一个三维场景，渲染出一张二维图像，主要由CPU & GPU协作完成。
渲染流程三个阶段：应用阶段 | 几何阶段 | 光栅化阶段

![渲染流程](1.png)

* 应用阶段：根据三维场景输出渲染所需要的几何信息（图元：点、线、三角面等）

    	三个步骤：

        1）数据加载到显存。

        2）设置渲染状态（使用哪个着色函数、光源属性等）。

        3）调用Draw Call（CPU向GPU发起渲染指令）

* 几何阶段：主要任务是把几何顶点坐标转换到屏幕空间中，然后交个光栅器处理

* 光栅化阶段：使用上阶段的数据产生屏幕像素，渲染成像。

两个主要任务：

* 计算每个图元覆盖了哪些像素

* 计算这些像素颜色

#### Draw Call（GPU流水线）：【几何阶段 & 光栅化阶段】
![GPU的渲染流水线实现。颜色表示了不同阶段的可配置性或可编程性：绿色表示该流水线阶段是完全可编程控制的，黄色表示该流水线阶段可以配置但不是可编程的，蓝色表示该流水线阶段是由GPU固定实现的，开发者没有任何控制权。实线表示该shader必须由开发者编程实现，虚线表示该Shader是可选的](2.png)

* 顶点着色器：主要实现顶点空间变换（坐标变换）、可实现定点着色（光照计算）等，基本任务把顶点位置坐标从模型空间转换到裁剪空间

* 曲面细分着色器：可选，细分图元，需要显卡支持。使模型看起来更细腻

* 裁剪：不在摄像机视野内的物体在此阶段被裁剪掉

* 屏幕映射：坐标转换（三维->二维），但需要记录下坐标深度、法线方向、视角方向等，跟用于显示的屏幕分辨率有关。

* 三角形设置：计算三角网格表示数据的过程，为计算三角面覆盖的像素准备数据

* 三角形遍历：检查每个像素是否被一个三角网格覆盖并生成图元。输出片元序列

* 片元着色器：输入，顶点着色器输出数据的插值。输出，一个或多个颜色值。纹理采样

* 逐片元操作：片元-->模板测试-->深度测试-->混合-->颜色缓冲

```
OpenGL & DirectX ：图像应用编程接口，用于渲染二维、三维图像。位于上层应用和GPU之间，应用程序通过这些编程接口发送渲染指令，由图像应用编程接口向显卡发送渲染指令
```


** 着色器语言：**

1）Direct X的HLSL（High Level Shading Language）

2）OpenGL的GLSL

3）NVIDIA的CG

4）Unity使用的是ShaderLab

#### 重要的数学基础：

** 1）矢量点积 **

    几何意义：投影

![几何意义](3.png)

a \* b = |a| \* |b| \* cosQ ** b在a上的投影 ** 

2）矢量叉积

几何意义：a X b得到同时垂直于a&b的新矢量

用途：计算垂直于一个平面、三角形的矢量。判断三角面的朝向

3）矩阵

几何意义：坐标变换（平移、缩放、旋转等，分别对应一变换矩阵）

用途：坐标空间变换

4）坐标空间

![](4.png)
![](5.png)

### ShaderLab语法
基本结构：

```
Shader "Custom Shaders/Simple Shader" {
    Properties {
         // 声明一个材质面板上的颜色拾取器
	_Color ("Color Tint", Color) = (1, 1, 1, 1)
    }
    SubShader {
        Pass {
            // CG代码开始
            CGPROGRAM
            // 声明顶点着色函数
            #pragma vertex vert
            // 声明片元着色函数
            #pragma fragment frag
            // 在CG程序中需要声明一个属性名称和类型都匹配的变量
            uniform fixed4 _Color;
	        struct a2v {
                // POSITION语义告诉Unity，用模型的顶点坐标填充vertex参数
                float4 vertex : POSITION;
                // NORMAL语义告诉Unity，用模型空间的法线方向填充normal参数
		float3 normal : NORMAL;
                // TEXCOORD0语义，告诉unity，用模型的第一套纹理坐标填充texcoord参数
		float4 texcoord : TEXCOORD0;
            };
            
            // 使用v2f结构体定义顶点着色器的输出
            struct v2f {
                // SV_POSITION语义告诉Unity，pos里包含了顶点在裁剪空间中的位置
                float4 pos : SV_POSITION;
                // COLOR0语义，用于存储颜色信息
                fixed3 color : COLOR0;
            };
            
            v2f vert(a2v v) {
                // 声明输出结构
            	v2f o;
            	o.pos = mul(UNITY_MATRIX_MVP, v.vertex);
                // v.normal保存了顶点的法线方向，分量范围[-1.0, 1.0],先将其映射到[0.0, 1.0],存到o.color传递给片元着色器
            	o.color = v.normal * 0.5 + fixed3(0.5, 0.5, 0.5);
                return o;
            }
            fixed4 frag(v2f i) : SV_Target {// SV_Target告诉渲染器，把用户的输出颜色存储到一个渲染目标中
            	fixed3 c = i.color;
            	c *= _Color.rgb;
                // 将插值后的值显示到屏幕上
                return fixed4(c, 1.0);
            }
            ENDCG
        }
    }
    FallBack "Diffuse"
}
```

CG中的语义：
![](6.png)
![](7.png)
![](9.png)
![](10.png)

### 基本光照&光照模型：
* 环境光：通常是一个全局变量

* 自发光：

* 漫反射（兰伯特光照模型）：

* 高光（镜面）反射（Phong光照模型）：
### 光照模型：
* Lambert模型：用来描述漫反射
```
计算公式：Cdiffuse = (Clight  * Mdiffuse ) Max(0, n * I)

n：表面法线；I：指向光源的单位矢量；Mdiffuse：材质的漫反射颜色；Clight：光源颜色
```

* Phong模型：模拟高光，可让物体表现出光斑
计算公式：![](11.png)
```
mgloss：是材质光泽度，mspecular：材质的高光反射颜色，Clight：光源颜色，v：视角方向，r：反射方向
```

* Blinn-Phong模型：基本原理同Phone，提高了运算效率；目前游戏上较流行的模型

* PBR：基于物理的渲染；使用BRDF（双向反射率分布方程）：主要描述了光线作用到物体表面后的反射（高光反射Specular）和散射（漫反射Diffuse）

### 光照计算：
* 1）逐像素光照：

        以每个像素为基础，得到他们的法线（对顶点法线插值得到，或从法线纹理采样得到），然后进行光照计算。

* 2）逐顶点光照

        在每个顶点上计算光照，然后在渲染图元内部进行线型插值，最后输出成像素颜色。

        由于顶点数目往往小于像素数目，所以逐顶点光照计算量少些

### 纹理：
* 漫反射纹理（漫反射贴图）

* 凹凸纹理（法线贴图、Heightmap）

* 渐变纹理

### 透明效果：
两种实现方式：1）透明度测试  2）透明度混合

* 透明度测试：不能实现真正的半透明，不需要关闭深度写入，实际上是根据透明度舍弃一些图元，所以他实现的效果要么完全透明，要么不透明。

* 透明度混合：可以实现真正的半透明，使用当前片元的透明度作为混合因子，与颜色缓存区中的颜色进行混合，得到新的颜色存入颜色缓存区中。需要关闭深度写入，深度缓存是只读的。

* 透明度混合方式关闭深度写入的原因：深度缓存区的剔除机制。

### 渲染顺序问题：
从距离摄像机由远及近依次渲染。

不考虑透明物体的情况下，unity使用深度缓冲区（z-buffer）的方式，使我们不用关心场景中物体的渲染顺序。

z-buffer基本思想：根据深度缓冲中的值判断该图片距离摄像机的距离，当渲染一个图元时，需要把他的深度值跟已经存到z-buffer中的值比较，如果距离摄像机更近，则这个片元覆盖掉z-buffer中的值，深度值写入z-buffer中。

### Unity Shader的渲染顺序：

采用渲染队列的方式解决：
![](12.png)

```
// 透明度测试
SubShader {
	Tags {"Queue": "AlphaTest"}
	Pass {
		...
	}
}
// 透明度混合
SubShader {
	Tags {"Queue": "Transparent"}
	Pass {
		ZWrite Off
		...
	}
}
```

### Unity 渲染路径
![](13.png)

### Unity Standard Sharder
![](14.png)

** 1、Rendering Mode ** 

Rendering Mode：在非透明和多种透明效果之间切换。

Opaque：默认，实体渲染。

Cutout：Alpha test，通过贴图的Alpha值缕空模型表面。

Transparent：透明效果，如玻璃，半透明塑料等等。

Fade：在这个模式下，一个对象可以实现淡入淡出效果。

参考：https://docs.unity3d.com/Manual/StandardShaderMaterialParameterRenderingMode.html

** 2、Albedo ** 

Albedo是一个只拥有颜色信息的“平面”贴图，即不带任何AO，SHADOW等光影信息。是物体的Base Color颜色值。

** 3、Metallic & Specluar & Smoothness ** 

Specular通过直接赋与颜色的方式来决定高光反射强度。Metallic则通过一个0~1的值，来决定金属的反射强度。

不管是在metallic还是Specular模式下，一但使用了贴图来决定高光反射效果。引擎将会采用贴图中的值，设置的Metallic因子，或者Specular Color均会无效。

Smoothness则决定了一个物体的光滑呈度。 即使一个物体表面高光很强烈。若它是一个不光滑的物体，那么其反射会呈不规则的方向分布，光会分散到不同的地方。那么到达人眼中的反射光就会少。整体的反射效果就会变得很弱。（注：当Metallic或者Specular被赋与贴图后。Smoothness值会失效。 转而采用Matallic或者Specular贴中的Alpha通道作为Smoothness值。）


** 4、Normal Map ** 

Normal Map是Bump Mapping的一种特例化。 它主要是通过贴图为光照计算时提供更细节的法线信息。使物体表面具有高度的细节效果。如下图所示


** 5、Heightmap ** 

Heightmap比NormalMap更上一层楼，NormalMap是通过赋与物体表面更多的法线信息，来造成光照上的细节增强。 Normal Map有一个缺点就是，当视线与表面平行时，就失去法线效果。而Heightmap则直接对某些顶点进行位移。由此也可以看出来，Heightmap的效率开销会比Normalmap高，要更据情况选择使用。

高度图是一张灰度图，白色表示突出，黑色表示凹陷。
![](15.png)

** 6、Occlusion Map **

Occlusion Map用于决定一个模型各部位受到间隔光照的影响情况。 间隔光照一般来自于Ambient和环境反射。
![](16.png)

** 7、Emission **

Emission表示一个物体的自发光程度。默认是纯黑，如果为这个物体赋值了非黑色的材质。 那么这个物体即使在黑暗的场景下，也会有亮光。

** 8、Detail Mask & Secondary Maps **

Secondary Maps用于在物体的表面增加细节。我们可以为一个物体再赋值一套Albedo和NormalMap. 第一套Albedo和第二套Albedo是叠加的。
![](17.png)

参考：https://docs.unity3d.com/Manual/StandardShaderMaterialParameterDetail.html

** 9、Fresnel **

Fresnel菲涅尔效果。物体的表面与视线的夹角的不同，会导致眼睛看到的从物体反射出来的光线的反射量不同。

Standard Shader通过Smoothness间接控制菲涅尔反射效果

参考：http://docs.unity3d.com/Manual/StandardShaderFresnel.html

PBR官方参考使用样例：

https://blogs.unity3d.com/2015/02/18/working-with-physically-based-shading-a-practical-approach/

![](18.png)